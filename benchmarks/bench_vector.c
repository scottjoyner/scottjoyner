// Portable, deterministic CPU vector scan benchmark. No private data or external libraries.
// Usage: cc -O3 -std=c11 bench_vector.c -lm -o bench_vector && ./bench_vector [N] [D] [Q] [R]
#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#include <float.h>
#include <limits.h>

#define K 5
static uint64_t state=20261029ULL;
// SplitMix64 avoids the short-period low-bit correlations of a simple LCG.
static uint64_t next_rng(void){
 uint64_t z=(state+=0x9e3779b97f4a7c15ULL);
 z=(z^(z>>30))*0xbf58476d1ce4e5b9ULL;
 z=(z^(z>>27))*0x94d049bb133111ebULL;
 return z^(z>>31);
}
static float rand_float(void){return (float)(next_rng()>>40)/8388607.5f-1.0f;}
static long long now_ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (long long)t.tv_sec*1000000000LL+t.tv_nsec;}
static int cmp_long(const void*a,const void*b){long long x=*(const long long*)a,y=*(const long long*)b;return(x>y)-(x<y);}
typedef struct {double score;size_t id;} Hit;
static void add_hit(Hit *h,double score,size_t id){
 for(int j=0;j<K;j++){
  if(score>h[j].score || (score==h[j].score && id<h[j].id)){
   for(int k=K-1;k>j;k--)h[k]=h[k-1];
   h[j]=(Hit){score,id};break;
  }
 }
}
static void reset(Hit *h){for(int k=0;k<K;k++)h[k]=(Hit){-DBL_MAX,SIZE_MAX};}
static int valid_hits(const Hit*h,size_t n){
 for(int j=0;j<K;j++){
  if(h[j].id>=n || !isfinite(h[j].score))return 0;
  for(int k=0;k<j;k++)if(h[k].id==h[j].id)return 0;
  if(j>0 && (h[j].score>h[j-1].score ||
      (h[j].score==h[j-1].score && h[j].id<=h[j-1].id)))return 0;
 }
 return 1;
}
static void fsearch(const float*base,const float*q,size_t n,size_t d,Hit*h){
 reset(h);
 for(size_t i=0;i<n;i++){
  const float*v=base+i*d;float acc=0.f;
  for(size_t j=0;j<d;j++)acc+=v[j]*q[j];
  add_hit(h,acc,i);
 }
}
static void isearch(const int8_t*base,const int8_t*q,size_t n,size_t d,Hit*h){
 reset(h);
 for(size_t i=0;i<n;i++){
  const int8_t*v=base+i*d;int64_t acc=0;
  for(size_t j=0;j<d;j++)acc+=(int)v[j]*(int)q[j];
  add_hit(h,(double)acc,i);
 }
}
static int8_t quant(float x){
 long k=lroundf(x*127.f);
 if(k>127) k=127;
 if(k< -127) k=-127;
 return(int8_t)k;
}
static void fill_unit(float *v,int8_t *v8,size_t d){
 double sum=0;
 for(size_t j=0;j<d;j++){v[j]=rand_float();sum+=(double)v[j]*(double)v[j];}
 double inv=1./sqrt(sum);
 for(size_t j=0;j<d;j++){v[j]=(float)(v[j]*inv);v8[j]=quant(v[j]);}
}
static double percent(long long*a,size_t count,double frac){
 long long *buf=malloc(count*sizeof(long long));
 if(!buf){fprintf(stderr,"allocation failed\n");exit(2);}
 memcpy(buf,a,count*sizeof(long long));qsort(buf,count,sizeof(long long),cmp_long);
 size_t ix=(size_t)ceil(frac*count)-1;double out=buf[ix]/1000000.0;free(buf);return out;
}
int main(int argc,char**argv){
 size_t n=argc>1?strtoul(argv[1],0,10):8192;
 size_t d=argc>2?strtoul(argv[2],0,10):384;
 size_t nq=argc>3?strtoul(argv[3],0,10):24;
 size_t repeats=argc>4?strtoul(argv[4],0,10):3;
 if(n<K||n>1000000||d<2||d>4096||nq<1||nq>500||repeats<1||repeats>100||n>SIZE_MAX/d){fprintf(stderr,"invalid bounds\n");return 2;}
 size_t cells=n*d,calls=nq*repeats;
 float*float_data=malloc(cells*sizeof(float));
 int8_t*int_data=malloc(cells);
 float*query=malloc(nq*d*sizeof(float));
 int8_t*query8=malloc(nq*d);
 long long*tf=calloc(calls,sizeof(long long)),*ti=calloc(calls,sizeof(long long));
 if(!float_data||!int_data||!query||!query8||!tf||!ti){fprintf(stderr,"allocation failed\n");return 2;}
 for(size_t i=0;i<n;i++)fill_unit(float_data+i*d,int_data+i*d,d);
 for(size_t i=0;i<nq;i++)fill_unit(query+i*d,query8+i*d,d);
 Hit a[K],b[K];double overlaps=0;int mismatches=0;
 // Warm both retrieval kernels, then measure the same query set.
 fsearch(float_data,query,n,d,a);
 isearch(int_data,query8,n,d,b);
 for(size_t r=0;r<repeats;r++){
  for(size_t i=0;i<nq;i++){
   size_t t=r*nq+i;
   long long start=now_ns();fsearch(float_data,query+i*d,n,d,a);tf[t]=now_ns()-start;
   start=now_ns();isearch(int_data,query8+i*d,n,d,b);ti[t]=now_ns()-start;
   int agree=0;
   for(int j=0;j<K;j++){
    for(int k=0;k<K;k++){if(a[j].id==b[k].id){agree++;break;}}
   }
   overlaps+=agree/(double)K;
   if(!valid_hits(a,n)||!valid_hits(b,n))mismatches++;
  }
 }
 char host[128]="unknown";gethostname(host,sizeof(host)-1);host[sizeof(host)-1]=0;
 printf("{\n");
 printf("  \"schema_version\": 1,\n  \"benchmark_kind\": \"synthetic_compiled_cpu_vector_scan\",\n");
 printf("  \"host\": \"%s\",\n  \"compiler\": \"%s\",\n",host,__VERSION__);
 printf("  \"seed\": 20261029,\n  \"vectors\": %zu,\n  \"dimensions\": %zu,\n  \"queries\": %zu,\n  \"repeats\": %zu,\n",n,d,nq,repeats);
 printf("  \"top_k\": 5,\n  \"total_calls_per_method\": %zu,\n",calls);
 printf("  \"float32_p50_ms\": %.6f,\n  \"float32_p95_ms\": %.6f,\n",percent(tf,calls,.5),percent(tf,calls,.95));
 printf("  \"int8_p50_ms\": %.6f,\n  \"int8_p95_ms\": %.6f,\n",percent(ti,calls,.5),percent(ti,calls,.95));
 printf("  \"int8_recall_at_5\": %.6f,\n  \"raw_float32_bytes\": %zu,\n  \"raw_int8_bytes\": %zu,\n",overlaps/calls,cells*4,cells);
 printf("  \"sanity_failures\": %d,\n  \"status\": \"%s\"\n}\n",mismatches,mismatches?"FAIL":"PASS");
 free(float_data);free(int_data);free(query);free(query8);free(tf);free(ti);
 return mismatches?1:0;
}
