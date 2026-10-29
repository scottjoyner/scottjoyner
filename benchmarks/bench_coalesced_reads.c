// Synthetic float32 reranking: rank-order pread, offset-sorted pread, and contiguous coalesced pread.
// gcc -O3 -Wall -Wextra -std=c11 bench_coalesced_reads.c -lm -o bench_coalesced_reads
// ./bench_coalesced_reads [n] [d] [queries] [repeats] [seed] [independent|clustered|temporal] [ram|pread_rank_warm|pread_sorted_warm|pread_coalesced_warm|pread_rank_hint|pread_sorted_hint|pread_coalesced_hint] [M=20|160]
// Independent processes are required for honest RSS comparisons.
// "hint" is best-effort fadvise/madvise; it does NOT guarantee a cold cache.
#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/mman.h>
#include <sys/resource.h>
#include <unistd.h>
#include <errno.h>
#include <limits.h>
#define K 5
#define MAXM 160
typedef struct { double score; size_t id; } Hit;
static uint64_t seed_state;
static uint64_t r64(void){
 uint64_t z=(seed_state+=UINT64_C(0x9e3779b97f4a7c15));
 z=(z^(z>>30))*UINT64_C(0xbf58476d1ce4e5b9);
 z=(z^(z>>27))*UINT64_C(0x94d049bb133111eb);
 return z^(z>>31);
}
static float rf(void){return(float)(r64()>>40)/8388607.5f-1.0f;}
static void normalize(float*x,size_t d){
 double norm=0;
 for(size_t j=0;j<d;j++)norm+=(double)x[j]*x[j];
 if(norm==0){fprintf(stderr,"zero norm\n");exit(2);}
 double s=1.0/sqrt(norm);
 for(size_t j=0;j<d;j++)x[j]=(float)(s*x[j]);
}
static void gen(float*x,size_t d){
 for(size_t j=0;j<d;j++)x[j]=rf();
 normalize(x,d);
}
static float scale_for(const float*x,size_t d){
 float max=0.f;
 for(size_t j=0;j<d;j++){float a=fabsf(x[j]);if(a>max)max=a;}
 return max>0.f ? max/127.f : 1.f/127.f;
}
static int8_t quant(float x,float scale){
 long j=lroundf(x/scale);
 if(j>127)j=127;
 if(j< -127)j=-127;
 return(int8_t)j;
}
static long long now_ns(void){
 struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
 return (long long)t.tv_sec*1000000000LL+t.tv_nsec;
}
static int ns_cmp(const void*a,const void*b){
 long long x=*(const long long*)a,y=*(const long long*)b;
 return(x>y)-(x<y);
}
static double ms_pct(long long*data,size_t n,double fraction){
 long long*v=malloc(n*sizeof(long long));
 if(!v){fprintf(stderr,"allocation failure\n");exit(2);}
 memcpy(v,data,n*sizeof(long long));
 qsort(v,n,sizeof(long long),ns_cmp);
 double answer=(double)v[(size_t)floor(fraction*(n-1))]/1e6;
 free(v);return answer;
}
static int hit_cmp(double s,size_t i,double t,size_t j){
 if(s>t)return -1;
 if(s<t)return 1;
 return(i>j)-(i<j);
}
static void init(Hit*h,int m){
 for(int j=0;j<m;j++)h[j]=(Hit){-INFINITY,SIZE_MAX};
}
static void add(Hit*h,int m,double score,size_t id){
 if(hit_cmp(score,id,h[m-1].score,h[m-1].id)>=0)return;
 int j=m-1;
 while(j>0&&hit_cmp(score,id,h[j-1].score,h[j-1].id)<0){
  h[j]=h[j-1];j--;
 }
 h[j]=(Hit){score,id};
}
static float dot32(const float*a,const float*b,size_t d){
 float score=0.f;
 for(size_t j=0;j<d;j++)score+=a[j]*b[j];
 return score;
}
static int64_t dot8(const int8_t*a,const int8_t*b,size_t d){
 int64_t score=0;
 for(size_t j=0;j<d;j++)score+=(int)a[j]*(int)b[j];
 return score;
}
static void exact(const float*x,const float*q,size_t n,size_t d,Hit*h){
 init(h,K);
 for(size_t i=0;i<n;i++)add(h,K,dot32(x+i*d,q,d),i);
}
static void shortlist(const int8_t*x,const float*scales,const int8_t*q,
                      size_t n,size_t d,int m,Hit*h){
 init(h,m);
 for(size_t i=0;i<n;i++){
  double v=(double)dot8(x+i*d,q,d)*(double)scales[i];
  add(h,m,v,i);
 }
}
static int count_hits(Hit*truth,Hit*result){
 int matched=0;
 for(int a=0;a<K;a++)for(int b=0;b<K;b++)if(truth[a].id==result[b].id){matched++;break;}
 return matched;
}
static int valid(Hit*h,int m,size_t n){
 for(int j=0;j<m;j++){
  if(h[j].id>=n||!isfinite(h[j].score))return 0;
  if(j&&hit_cmp(h[j-1].score,h[j-1].id,h[j].score,h[j].id)>0)return 0;
  for(int k=0;k<j;k++)if(h[k].id==h[j].id)return 0;
 }
 return 1;
}
static int write_all(int fd,const void*buf,size_t len){
 const char*p=buf;
 while(len){
  ssize_t n=write(fd,p,len);
  if(n<0){if(errno==EINTR)continue;return -1;}
  if(n==0)return -1;
  p+=n;len-=(size_t)n;
 }
 return 0;
}
static int pread_all(int fd,void*buf,size_t len,off_t off){
 char*p=buf;
 while(len){
  ssize_t k=pread(fd,p,len,off);
  if(k<0){if(errno==EINTR)continue;return -1;}
  if(k==0)return -1;
  len-=(size_t)k;p+=k;off+=k;
 }
 return 0;
}
static long rss_kib(void){
 FILE*f=fopen("/proc/self/status","r");if(!f)return -1;
 char line[256];long rss=-1;
 while(fgets(line,sizeof(line),f))if(sscanf(line,"VmRSS: %ld kB",&rss)==1)break;
 fclose(f);return rss;
}
static int cmp_size(const void*a,const void*b){
 size_t x=*(const size_t*)a,y=*(const size_t*)b;
 return (x>y)-(x<y);
}
static int bad(const char*message){
 fprintf(stderr,"BENCH_ERROR %s: %s\n",message,strerror(errno));return 2;
}
int main(int argc,char**argv){
 size_t n=argc>1?strtoull(argv[1],0,10):8192;
 size_t d=argc>2?strtoull(argv[2],0,10):768;
 size_t nq=argc>3?strtoull(argv[3],0,10):12;
 size_t reps=argc>4?strtoull(argv[4],0,10):2;
 uint64_t s=argc>5?strtoull(argv[5],0,10):20261029;
 const char*distribution=argc>6?argv[6]:"clustered";
 const char*mode=argc>7?argv[7]:"ram";
 int m=argc>8?atoi(argv[8]):20;
 if(n<160||n>100000||d<2||d>4096||nq<1||nq>128||reps<1||reps>10||
    n>SIZE_MAX/d||nq>SIZE_MAX/d||n*d>SIZE_MAX/sizeof(float)||
    (m!=20&&m!=160)||
    (strcmp(distribution,"clustered")&&strcmp(distribution,"temporal")&&strcmp(distribution,"independent"))||
    (strcmp(mode,"ram")&&strcmp(mode,"pread_rank_warm")&&
     strcmp(mode,"pread_sorted_warm")&&strcmp(mode,"pread_coalesced_warm")&&
     strcmp(mode,"pread_rank_hint")&&strcmp(mode,"pread_sorted_hint")&&
     strcmp(mode,"pread_coalesced_hint"))){
  fprintf(stderr,"invalid bounded workload\n");return 2;
 }
 const int ram=!strcmp(mode,"ram");
 const int sorted=strstr(mode,"sorted")!=NULL;
 const int coalesced=strstr(mode,"coalesced")!=NULL;
 const int hinted=strstr(mode,"_hint")!=NULL;
 size_t vector_bytes=n*d*sizeof(float),query_bytes=nq*d*sizeof(float);
 seed_state=s;
 long long t_init=now_ns();
 float*x=malloc(vector_bytes),*q=malloc(query_bytes);
 int8_t*x8=malloc(n*d),*q8=malloc(nq*d);
 float*scales=malloc(n*sizeof(float));
 Hit*truth=calloc(nq*K,sizeof(Hit));
 if(!x||!q||!x8||!q8||!scales||!truth)return bad("buffer allocation");
 for(size_t i=0;i<n;i++){
  float*vec=x+i*d;gen(vec,d);
  if(!strcmp(distribution,"temporal")&&i%256!=0){
   const float*prev=x+(i-1)*d;
   for(size_t j=0;j<d;j++)vec[j]=.995f*prev[j]+.10f*vec[j];
   normalize(vec,d);
  }else if(!strcmp(distribution,"clustered")&&i>=32){
   const float*center=x+(i%32)*d;
   for(size_t j=0;j<d;j++)vec[j]=.85f*center[j]+.35f*vec[j];
   normalize(vec,d);
  }
 }
 for(size_t i=0;i<nq;i++){
  float*vec=q+i*d;gen(vec,d);
  if(strcmp(distribution,"independent")){
   const float*anchor=x+(r64()%n)*d;
   for(size_t j=0;j<d;j++)vec[j]=.995f*anchor[j]+.03f*vec[j];
   normalize(vec,d);
  }
 }
 double synthetic_generation_ms=(now_ns()-t_init)/1e6;
 long long t_prep=now_ns();
 for(size_t i=0;i<n;i++){
  const float*vec=x+i*d;
  float z=scale_for(vec,d);scales[i]=z;
  for(size_t j=0;j<d;j++)x8[i*d+j]=quant(vec[j],z);
 }
 for(size_t i=0;i<nq;i++){
  const float*vec=q+i*d;
  float z=scale_for(vec,d);
  for(size_t j=0;j<d;j++)q8[i*d+j]=quant(vec[j],z);
 }
 double quant_ms=(now_ns()-t_prep)/1e6;
 for(size_t i=0;i<nq;i++)exact(x,q+i*d,n,d,truth+i*K);
 long long*exact_t=calloc(nq*reps,sizeof(long long));
 if(!exact_t)return bad("oracle timing allocation");
 for(size_t i=0;i<nq*reps;i++){
  long long start=now_ns();
  Hit baseline[K];
  exact(x,q+(i%nq)*d,n,d,baseline);
  exact_t[i]=now_ns()-start;
  if(!valid(baseline,K,n))return bad("invalid oracle");
 }
 int fd=-1;
 long long io_prep_start=now_ns();
 int advised_failures=0;
 if(!ram){
  char name[]="/tmp/bench-sensorgraft-rerank-XXXXXX";
  fd=mkstemp(name);
  if(fd<0)return bad("mkstemp");
  if(unlink(name)<0)return bad("unlink benchmark tmp");
  if(write_all(fd,x,vector_bytes)<0)return bad("write synthetic backing file");
  if(hinted && fsync(fd)<0)return bad("fsync before fadvise");
  // Save memory in file-backed modes; no full float32 x array retained.
  free(x);x=NULL;
 }
 double io_build_ms=(now_ns()-io_prep_start)/1e6;
 long rss_ready=rss_kib();
 float*buf=malloc((size_t)m*d*sizeof(float));
 long long*totals=calloc(nq*reps,sizeof(long long));
 long long*scans=calloc(nq*reps,sizeof(long long));
 long long*fetches=calloc(nq*reps,sizeof(long long));
 if(!buf||!totals||!scans||!fetches)return bad("query allocation");
 struct rusage before,after;
 getrusage(RUSAGE_SELF,&before);
 Hit cand[MAXM],res[K];
 // Warm search and candidate retrieval (warm modes retain Linux page cache).
 shortlist(x8,scales,q8,n,d,m,cand);
 if(!ram){
  // Warm the candidate file pages before measured queries (warm-path intent).
  for(int j=0;j<m;j++)if(pread_all(fd,buf,d*sizeof(float),
       (off_t)(cand[j].id*d*sizeof(float)))<0)return bad("warm pread");
 }
 long long read_bytes=0,read_calls=0,coalesced_runs=0,adjacent_pairs=0;
 int hits=0,sanity=0;
 for(size_t rep=0;rep<reps;rep++)for(size_t qi=0;qi<nq;qi++){
  size_t idx=rep*nq+qi;
  const float*query=q+qi*d;
  if(hinted && posix_fadvise(fd,0,(off_t)vector_bytes,POSIX_FADV_DONTNEED)!=0)
   advised_failures++;
  long long start=now_ns();
  shortlist(x8,scales,q8+qi*d,n,d,m,cand);
  long long scan_done=now_ns();
  init(res,K);
  if(ram){
   for(int j=0;j<m;j++)add(res,K,dot32(x+cand[j].id*d,query,d),cand[j].id);
  }else if(!sorted&&!coalesced){
   // Candidate rank order, single pread per candidate.
   for(int j=0;j<m;j++){
    size_t id=cand[j].id;
    if(pread_all(fd,buf,d*sizeof(float),(off_t)(id*d*sizeof(float)))<0)
     return bad("ranked candidate pread");
    read_calls++;read_bytes+=(long long)(d*sizeof(float));
    add(res,K,dot32(buf,query,d),id);
   }
  }else{
   size_t ids[MAXM];
   for(int j=0;j<m;j++)ids[j]=cand[j].id;
   qsort(ids,m,sizeof(size_t),cmp_size);
   for(int j=1;j<m;j++)if(ids[j]==ids[j-1])sanity++;
   if(sorted){
    // Physical offset order, one pread per candidate.
    for(int j=0;j<m;j++){
     size_t id=ids[j];
     if(pread_all(fd,buf,d*sizeof(float),(off_t)(id*d*sizeof(float)))<0)
      return bad("sorted candidate pread");
     read_calls++;read_bytes+=(long long)(d*sizeof(float));
     add(res,K,dot32(buf,query,d),id);
    }
   }else{
    // Exact adjacent candidate IDs share one read into a preallocated buffer.
    int j=0;
    while(j<m){
     int end=j+1;
     while(end<m && ids[end]==ids[end-1]+1)end++;
     size_t count=(size_t)(end-j);
     size_t bytes=count*d*sizeof(float);
     if(count>1)adjacent_pairs+=(long long)count-1;
     if(pread_all(fd,buf,bytes,(off_t)(ids[j]*d*sizeof(float)))<0)
      return bad("coalesced candidate pread");
     read_calls++;coalesced_runs++;read_bytes+=(long long)bytes;
     for(int z=j;z<end;z++){
      size_t id=ids[z];
      add(res,K,dot32(buf+(size_t)(z-j)*d,query,d),id);
     }
     j=end;
    }
   }
  }
  long long done=now_ns();
  totals[idx]=done-start;scans[idx]=scan_done-start;fetches[idx]=done-scan_done;
  if(!valid(cand,m,n)||!valid(res,K,n))sanity++;
  if(rep==0)hits+=count_hits(truth+qi*K,res);
 }
 getrusage(RUSAGE_SELF,&after);
 long rss_after=rss_kib();
 if(fd>=0&&close(fd)<0)return bad("close");
 char host[128]="unknown";gethostname(host,sizeof(host)-1);host[sizeof(host)-1]=0;
 printf("{\"schema_version\":1,\"kind\":\"synthetic_coalesced_candidate_io_cpu\","
        "\"host\":\"%s\",\"compiler\":\"%s\","
        "\"seed\":%llu,\"distribution\":\"%s\",\"mode\":\"%s\","
        "\"vectors\":%zu,\"dimensions\":%zu,\"queries\":%zu,\"repeats\":%zu,"
        "\"top_k\":5,\"shortlist_m\":%d,"
        "\"float32_reference_p50_ms\":%.6f,"
        "\"synthetic_generation_ms\":%.6f,"
        "\"quantization_ms\":%.6f,\"backing_file_setup_ms\":%.6f,"
        "\"backing_file_size_bytes\":%zu,\"int8_bytes\":%zu,"
        "\"int8_scale_bytes\":%zu,\"float32_resident_in_heap\":%s,"
        "\"rss_after_build_kib\":%ld,\"rss_after_query_kib\":%ld,"
        "\"read_calls\":%lld,\"read_bytes\":%lld,\"coalesced_runs\":%lld,\"adjacent_pairs\":%lld,\"hint_failures\":%d,"
        "\"minor_faults_delta\":%ld,\"major_faults_delta\":%ld,"
        "\"recall_at5\":%.8f,\"hits\":%d,\"opportunities\":%zu,"
        "\"query_p50_ms\":%.6f,\"query_p95_ms\":%.6f,"
        "\"scan_p50_ms\":%.6f,\"rerank_fetch_p50_ms\":%.6f,"
        "\"sanity_failures\":%d,\"status\":\"%s\"}\n",
        host,__VERSION__,(unsigned long long)s,distribution,mode,
        n,d,nq,reps,m,ms_pct(exact_t,nq*reps,.5),
        synthetic_generation_ms,quant_ms,io_build_ms,ram?0:vector_bytes,n*d,n*sizeof(float),
        ram?"true":"false",rss_ready,rss_after,read_calls,read_bytes,coalesced_runs,adjacent_pairs,advised_failures,
        after.ru_minflt-before.ru_minflt,after.ru_majflt-before.ru_majflt,
        (double)hits/(nq*K),hits,nq*K,
        ms_pct(totals,nq*reps,.5),ms_pct(totals,nq*reps,.95),
        ms_pct(scans,nq*reps,.5),ms_pct(fetches,nq*reps,.5),
        sanity,sanity?"FAIL":"PASS");
 free(x);free(q);free(x8);free(q8);free(scales);free(truth);
 free(exact_t);free(buf);free(totals);free(scans);free(fetches);
 return sanity?1:0;
}
