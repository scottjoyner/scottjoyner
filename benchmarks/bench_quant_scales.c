// Synthetic CPU float32 vs int8 retrieval with fixed and per-vector scales.
// Build: gcc -O3 -Wall -Wextra -std=c11 benchmarks/bench_quant_scales.c -lm -o /tmp/bench_quant_scales
// Run: /tmp/bench_quant_scales [n=8192] [dim=768] [queries=12] [repeats=2] [seed=20261029] [independent|temporal|clustered]
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#define K 5
#define NC 4
#define MAX_M 160
static const int ms[NC]={20,40,80,160};
typedef struct {double score;size_t id;} Hit;
typedef struct {
  int8_t *v,*q;
  float *scales,*query_scales;
  long long *times[NC];
  double recall_hits[NC];
  double prep_ms;
} Scheme;
static uint64_t rnd;
static uint64_t rand64(void){
 uint64_t z=(rnd+=UINT64_C(0x9e3779b97f4a7c15));
 z=(z^(z>>30))*UINT64_C(0xbf58476d1ce4e5b9);
 z=(z^(z>>27))*UINT64_C(0x94d049bb133111eb);
 return z^(z>>31);
}
static float random_float(void){return(float)(rand64()>>40)/8388607.5f-1.0f;}
static void normalize(float *v,size_t d){
 double ss=0;
 for(size_t j=0;j<d;j++)ss+=(double)v[j]*v[j];
 if(ss<=0){fprintf(stderr,"invalid synthetic norm\n");exit(2);}
 double inv=1/sqrt(ss);
 for(size_t j=0;j<d;j++)v[j]=(float)(v[j]*inv);
}
static void generate(float *v,size_t d){
 for(size_t j=0;j<d;j++)v[j]=random_float();
 normalize(v,d);
}
static int8_t quant(float v,float scale){
 long q=lroundf(v/scale);
 if(q>127)q=127; else if(q<-127)q=-127;
 return(int8_t)q;
}
static float absmax_scale(const float*v,size_t d){
 float m=0;
 for(size_t j=0;j<d;j++){float a=fabsf(v[j]);if(a>m)m=a;}
 return m>0 ? m/127.f : 1.f/127.f;
}
static int cmp_hit(double s,size_t i,double t,size_t j){
 if(s>t)return -1;
 if(s<t)return 1;
 return (i>j)-(i<j);
}
static void init(Hit *h,int m){
 for(int i=0;i<m;i++)h[i]=(Hit){-INFINITY,SIZE_MAX};
}
static void add(Hit *h,int m,double score,size_t id){
 if(cmp_hit(score,id,h[m-1].score,h[m-1].id)>=0)return;
 int j=m-1;
 while(j>0 && cmp_hit(score,id,h[j-1].score,h[j-1].id)<0){
  h[j]=h[j-1];j--;
 }
 h[j]=(Hit){score,id};
}
static int valid(Hit*h,int m,size_t n){
 for(int i=0;i<m;i++){
  if(h[i].id>=n||!isfinite(h[i].score))return 0;
  if(i>0 && cmp_hit(h[i-1].score,h[i-1].id,h[i].score,h[i].id)>0)return 0;
  for(int j=0;j<i;j++)if(h[i].id==h[j].id)return 0;
 }
 return 1;
}
static float dot32(const float*a,const float*b,size_t d){
 float s=0;
 for(size_t j=0;j<d;j++)s+=a[j]*b[j];
 return s;
}
static int64_t dot8(const int8_t*a,const int8_t*b,size_t d){
 int64_t v=0;
 for(size_t j=0;j<d;j++)v+=(int)a[j]*(int)b[j];
 return v;
}
static void exact(const float*v,const float*q,size_t n,size_t d,Hit*out){
 init(out,K);
 for(size_t i=0;i<n;i++)add(out,K,dot32(v+i*d,q,d),i);
}
static void approx(const Scheme*s,const int8_t*q,size_t n,size_t d,Hit*out){
 init(out,MAX_M);
 for(size_t i=0;i<n;i++){
  // q scale is common for all candidates of this query; can be omitted.
  double score=(double)dot8(s->v+i*d,q,d)*(double)s->scales[i];
  add(out,MAX_M,score,i);
 }
}
static void rerank(Hit*shortlist,int m,const float*v,const float*q,size_t d,Hit*out){
 init(out,K);
 for(int j=0;j<m;j++){
  size_t i=shortlist[j].id;
  add(out,K,dot32(v+i*d,q,d),i);
 }
}
static int hits(Hit*a,Hit*b){
 int k=0;
 for(int i=0;i<K;i++)for(int j=0;j<K;j++)if(a[i].id==b[j].id){k++;break;}
 return k;
}
static long long ns(void){
 struct timespec ts;clock_gettime(CLOCK_MONOTONIC,&ts);
 return (long long)ts.tv_sec*1000000000LL+ts.tv_nsec;
}
static int cmp_ns(const void*a,const void*b){
 long long x=*(const long long*)a,y=*(const long long*)b;
 return(x>y)-(x<y);
}
static double pct(const long long*a,size_t n,double q){
 long long *b=malloc(n*sizeof(*b));
 if(!b){fprintf(stderr,"timing memory failed\n");exit(2);}
 memcpy(b,a,n*sizeof(*b));qsort(b,n,sizeof(*b),cmp_ns);
 size_t pos=(size_t)floor(q*(n-1));double ans=b[pos]/1e6;
 free(b);return ans;
}
static void prep_scheme(Scheme*s,const float*v,const float*q,size_t n,size_t d,size_t nq,int dynamic){
 long long start=ns();
 s->v=malloc(n*d);
 s->q=malloc(nq*d);
 s->scales=malloc(n*sizeof(float));
 s->query_scales=malloc(nq*sizeof(float));
 if(!s->v||!s->q||!s->scales||!s->query_scales){fprintf(stderr,"quant allocation failure\n");exit(2);}
 for(size_t i=0;i<n;i++){
  const float*p=v+i*d;
  float scale=dynamic ? absmax_scale(p,d) : 1.f/127.f;
  s->scales[i]=scale;
  for(size_t j=0;j<d;j++)s->v[i*d+j]=quant(p[j],scale);
 }
 for(size_t i=0;i<nq;i++){
  const float*p=q+i*d;
  float scale=dynamic ? absmax_scale(p,d) : 1.f/127.f;
  s->query_scales[i]=scale;
  for(size_t j=0;j<d;j++)s->q[i*d+j]=quant(p[j],scale);
 }
 s->prep_ms=(ns()-start)/1e6;
}
int main(int argc,char**argv){
 size_t n=argc>1?strtoull(argv[1],0,10):8192;
 size_t d=argc>2?strtoull(argv[2],0,10):768;
 size_t nq=argc>3?strtoull(argv[3],0,10):12;
 size_t reps=argc>4?strtoull(argv[4],0,10):2;
 uint64_t seed=argc>5?strtoull(argv[5],0,10):20261029;
 const char*mode=argc>6?argv[6]:"independent";
 if(n<MAX_M||n>100000||d<2||d>4096||nq<1||nq>100||reps<1||reps>10 ||
    n>SIZE_MAX/d||nq>SIZE_MAX/d ||
    (strcmp(mode,"independent")&&strcmp(mode,"clustered")&&strcmp(mode,"temporal"))){
  fprintf(stderr,"bad arguments\n");return 2;
 }
 rnd=seed;
 float*v=malloc(n*d*sizeof(float)),*q=malloc(nq*d*sizeof(float));
 long long*exact_t=calloc(nq*reps,sizeof(long long));
 if(!v||!q||!exact_t){fprintf(stderr,"benchmark allocation failure\n");return 2;}
 for(size_t i=0;i<n;i++){
  float*p=v+i*d;generate(p,d);
  if(!strcmp(mode,"temporal")&&i%256!=0){
   const float*prev=v+(i-1)*d;
   for(size_t j=0;j<d;j++)p[j]=.995f*prev[j]+.10f*p[j];
   normalize(p,d);
  }else if(!strcmp(mode,"clustered")&&i>=32){
   const float*center=v+(i%32)*d;
   for(size_t j=0;j<d;j++)p[j]=.85f*center[j]+.35f*p[j];
   normalize(p,d);
  }
 }
 for(size_t i=0;i<nq;i++){
  float*p=q+i*d;generate(p,d);
  if(strcmp(mode,"independent")){
   const float*anchor=v+(rand64()%n)*d;
   for(size_t j=0;j<d;j++)p[j]=.995f*anchor[j]+.03f*p[j];
   normalize(p,d);
  }
 }
 Scheme schemes[2]={0};
 prep_scheme(&schemes[0],v,q,n,d,nq,0);
 prep_scheme(&schemes[1],v,q,n,d,nq,1);
 for(int z=0;z<2;z++)for(int m=0;m<NC;m++){
  schemes[z].times[m]=calloc(nq*reps,sizeof(long long));
  if(!schemes[z].times[m]){fprintf(stderr,"timing allocation failure\n");return 2;}
 }
 Hit truth[K],neighbors[MAX_M],reranked[K];
 exact(v,q,n,d,truth);
 for(int z=0;z<2;z++)approx(&schemes[z],schemes[z].q,n,d,neighbors);
 int failures=0;
 for(size_t rep=0;rep<reps;rep++)for(size_t qi=0;qi<nq;qi++){
  size_t index=rep*nq+qi;
  const float*query=q+qi*d;
  long long start=ns();
  exact(v,query,n,d,truth);
  exact_t[index]=ns()-start;
  // Alternate scheme order by query and repetition to mitigate warm-order bias.
  for(int pass=0;pass<2;pass++){
   int z=(int)((pass+rep+qi)%2);
   Scheme*s=&schemes[z];
   start=ns();
   approx(s,s->q+qi*d,n,d,neighbors);
   long long scan_done=ns();
   if(!valid(neighbors,MAX_M,n))failures++;
   for(int m=0;m<NC;m++){
    // Timed directly from start of the scan; the same shortlist scan feeds all options.
    long long begin_rerank=ns();
    rerank(neighbors,ms[m],v,query,d,reranked);
    long long done=ns();
    if(!valid(reranked,K,n))failures++;
    s->times[m][index]=(scan_done-start)+(done-begin_rerank);
    if(rep==0)s->recall_hits[m]+=hits(truth,reranked);
   }
  }
 }
 char host[128]="unknown";
 gethostname(host,sizeof(host)-1);host[sizeof(host)-1]=0;
 printf("{\"schema_version\":1,\"kind\":\"synthetic_fixed127_vs_absmax_int8_rerank\","
        "\"host\":\"%s\",\"compiler\":\"%s\",\"seed\":%llu,"
        "\"distribution\":\"%s\",\"vectors\":%zu,\"dimensions\":%zu,"
        "\"queries\":%zu,\"repeats\":%zu,\"float32_exact_p50_ms\":%.6f,"
        "\"float32_exact_p95_ms\":%.6f,\"schemes\":[",
        host,__VERSION__,(unsigned long long)seed,mode,n,d,nq,reps,
        pct(exact_t,nq*reps,.5),pct(exact_t,nq*reps,.95));
 for(int z=0;z<2;z++){
  Scheme*s=&schemes[z];
  printf("%s{\"name\":\"%s\",\"quantize_precompute_ms\":%.6f,"
         "\"raw_vector_bytes\":%zu,\"scale_metadata_bytes\":%zu,"
         "\"topk_results\":[",
         z?",":"",z?"per_vector_absmax":"fixed127",s->prep_ms,n*d,n*sizeof(float));
  for(int m=0;m<NC;m++){
   double rec=s->recall_hits[m]/(nq*K);
   printf("%s{\"candidates\":%d,\"recall_at5\":%.8f,\"hits\":%.0f,"
          "\"query_p50_ms\":%.6f,\"query_p95_ms\":%.6f}",
          m?",":"",ms[m],rec,s->recall_hits[m],
          pct(s->times[m],nq*reps,.5),pct(s->times[m],nq*reps,.95));
  }
  printf("]}");
 }
 printf("],\"sanity_failures\":%d,\"status\":\"%s\"}\n",failures,failures?"FAIL":"PASS");
 for(int z=0;z<2;z++){
  Scheme*s=&schemes[z];
  free(s->v);free(s->q);free(s->scales);free(s->query_scales);
  for(int m=0;m<NC;m++)free(s->times[m]);
 }
 free(v);free(q);free(exact_t);
 return failures?1:0;
}
