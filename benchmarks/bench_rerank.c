// Public, dependency-free, synthetic int8 shortlist + exact float32 reranking benchmark.
// Compile: gcc -O3 -Wall -Wextra -std=c11 bench_rerank.c -lm -o bench_rerank
// Run: ./bench_rerank [vectors=8192] [dimensions=768] [queries=12] [repeats=2] [seed=20261029]
#define _POSIX_C_SOURCE 200809L
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <math.h>
#include <time.h>
#include <unistd.h>
#define K 5
#define MAX_CANDIDATES 160
static const int candidates[]={5,10,20,40,80,160};
#define NC (sizeof(candidates)/sizeof(candidates[0]))
typedef struct {double score;size_t id;} Hit;
static uint64_t state;
static uint64_t rand64(void) {
 uint64_t z=(state+=UINT64_C(0x9e3779b97f4a7c15));
 z=(z^(z>>30))*UINT64_C(0xbf58476d1ce4e5b9);
 z=(z^(z>>27))*UINT64_C(0x94d049bb133111eb);
 return z^(z>>31);
}
static float rand_float(void) { return (float)(rand64()>>40)/8388607.5f-1.0f; }
static int8_t quant(float x) {
 long i=lroundf(x*127.f);
 if(i>127)i=127;
 if(i< -127)i=-127;
 return (int8_t)i;
}
static void gen(float *v,size_t d) {
 double m=0;
 for(size_t j=0;j<d;j++){v[j]=rand_float();m+=(double)v[j]*v[j];}
 double inv=1.0/sqrt(m);
 for(size_t j=0;j<d;j++)v[j]=(float)(v[j]*inv);
}
static int cmp_hit(double x,size_t ix,double y,size_t iy) {
 if(x>y)return -1;
 if(x<y)return 1;
 return (ix>iy)-(ix<iy);
}
static void add(Hit *out,int len,double score,size_t id) {
 if(cmp_hit(score,id,out[len-1].score,out[len-1].id)>=0)return;
 int j=len-1;
 while(j>0&&cmp_hit(score,id,out[j-1].score,out[j-1].id)<0) {
  out[j]=out[j-1];j--;
 }
 out[j]=(Hit){score,id};
}
static void init(Hit*out,int k) {
 for(int i=0;i<k;i++)out[i]=(Hit){-INFINITY,SIZE_MAX};
}
static int valid(Hit *h,int len,size_t n) {
 for(int i=0;i<len;i++) {
  if(h[i].id>=n||!isfinite(h[i].score))return 0;
  for(int j=0;j<i;j++)if(h[i].id==h[j].id)return 0;
  if(i>0&&cmp_hit(h[i-1].score,h[i-1].id,h[i].score,h[i].id)>0)return 0;
 }
 return 1;
}
static float dot32(const float*a,const float*b,size_t d) {
 float s=0.f;
 for(size_t j=0;j<d;j++)s+=a[j]*b[j];
 return s;
}
static int64_t dot8(const int8_t*a,const int8_t*b,size_t d) {
 int64_t s=0;
 for(size_t j=0;j<d;j++)s+=(int)a[j]*(int)b[j];
 return s;
}
static void exact(const float*x,const float*q,size_t n,size_t d,Hit *out) {
 init(out,K);
 for(size_t i=0;i<n;i++)add(out,K,dot32(x+i*d,q,d),i);
}
static void approx_candidates(const int8_t*x,const int8_t*q,size_t n,size_t d,Hit*out) {
 init(out,MAX_CANDIDATES);
 for(size_t i=0;i<n;i++)add(out,MAX_CANDIDATES,(double)dot8(x+i*d,q,d),i);
}
static void rescore(const Hit*candidates_in,int n,const float*x,const float*q,size_t d,Hit*out) {
 init(out,K);
 for(int i=0;i<n;i++) {
  size_t id=candidates_in[i].id;
  add(out,K,dot32(x+id*d,q,d),id);
 }
}
static double recall(Hit*a,Hit*b) {
 int equal=0;
 for(int i=0;i<K;i++)for(int j=0;j<K;j++) {
  if(a[i].id==b[j].id){equal++;break;}
 }
 return (double)equal/K;
}
static long long ns(void) {
 struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);
 return (long long)t.tv_sec*1000000000LL+t.tv_nsec;
}
static int compare_ns(const void*a,const void*b) {
 long long x=*(const long long*)a,y=*(const long long*)b;
 return(x>y)-(x<y);
}
static double p50_ms(long long*values,size_t n) {
 long long *copy=malloc(n*sizeof(long long));
 if(!copy){fprintf(stderr,"timing allocation failed\n");exit(2);}
 memcpy(copy,values,n*sizeof(long long));
 qsort(copy,n,sizeof(long long),compare_ns);
 double v=copy[(n-1)/2]/1e6;free(copy);return v;
}
int main(int argc,char**argv) {
 size_t n=argc>1?strtoull(argv[1],0,10):8192;
 size_t d=argc>2?strtoull(argv[2],0,10):768;
 size_t nq=argc>3?strtoull(argv[3],0,10):12;
 size_t repeats=argc>4?strtoull(argv[4],0,10):2;
 uint64_t seed=argc>5?strtoull(argv[5],0,10):UINT64_C(20261029);
 if(n<MAX_CANDIDATES || n>200000 || d<2 || d>4096 || nq<1 || nq>500 ||
     repeats<1 || repeats>30 || n>SIZE_MAX/d || nq>SIZE_MAX/d) {
  fprintf(stderr,"invalid workload bounds\n");return 2;
 }
 state=seed; size_t calls=nq*repeats;
 float *x=malloc(n*d*sizeof(float)), *q=malloc(nq*d*sizeof(float));
 int8_t *x8=malloc(n*d),*q8=malloc(nq*d);
 long long *base_t=calloc(calls,sizeof(long long));
 long long *short_t=calloc(calls,sizeof(long long));
 long long *rescore_t[NC];double total_recall[NC]={0};
 for(size_t m=0;m<NC;m++)rescore_t[m]=calloc(calls,sizeof(long long));
 if(!x||!q||!x8||!q8||!base_t||!short_t) {
  fprintf(stderr,"allocation failed\n");return 2;
 }
 for(size_t m=0;m<NC;m++)if(!rescore_t[m]){fprintf(stderr,"allocation failed\n");return 2;}
 for(size_t i=0;i<n;i++)gen(x+i*d,d);
 for(size_t i=0;i<nq;i++)gen(q+i*d,d);
 long long start=ns();
 for(size_t i=0;i<n*d;i++)x8[i]=quant(x[i]);
 for(size_t i=0;i<nq*d;i++)q8[i]=quant(q[i]);
 double quant_ms=(ns()-start)/1e6;
 Hit base[K], shortlist[MAX_CANDIDATES], reranked[K];
 int checks=0;
 // Warm caches and kernels.
 exact(x,q,n,d,base);
 approx_candidates(x8,q8,n,d,shortlist);
 for(size_t r=0;r<repeats;r++)for(size_t z=0;z<nq;z++) {
  size_t t=r*nq+z;
  const float*query=q+z*d;const int8_t*query8=q8+z*d;
  start=ns();exact(x,query,n,d,base);base_t[t]=ns()-start;
  start=ns();approx_candidates(x8,query8,n,d,shortlist);short_t[t]=ns()-start;
  if(!valid(base,K,n)||!valid(shortlist,MAX_CANDIDATES,n))checks++;
  for(size_t m=0;m<NC;m++) {
   start=ns();rescore(shortlist,candidates[m],x,query,d,reranked);
   rescore_t[m][t]=ns()-start;
   if(!valid(reranked,K,n))checks++;
   total_recall[m]+=recall(base,reranked);
  }
 }
 char host[128]="unknown";gethostname(host,sizeof(host)-1);host[sizeof(host)-1]=0;
 printf("{\n  \"schema_version\": 1,\n  \"kind\": \"synthetic_cpu_int8_shortlist_float32_rerank\",\n");
 printf("  \"host\": \"%s\",\n  \"compiler\": \"%s\",\n",host,__VERSION__);
 printf("  \"seed\": %llu,\n  \"vectors\": %zu,\n  \"dimensions\": %zu,\n",
        (unsigned long long)seed,n,d);
 printf("  \"queries\": %zu,\n  \"repeats\": %zu,\n  \"top_k\": %d,\n",nq,repeats,K);
 printf("  \"raw_float32_bytes\": %zu,\n  \"raw_int8_bytes\": %zu,\n",n*d*4,n*d);
 printf("  \"quantize_vectors_and_queries_ms\": %.6f,\n",quant_ms);
 printf("  \"exact_float32_p50_ms\": %.6f,\n",p50_ms(base_t,calls));
 printf("  \"int8_shortlist_top160_p50_ms\": %.6f,\n",p50_ms(short_t,calls));
 printf("  \"options\": [\n");
 for(size_t m=0;m<NC;m++) {
  printf("    {\"candidates\": %d, \"recall_at_5\": %.6f, \"rerank_only_p50_ms\": %.6f, ",
         candidates[m],total_recall[m]/calls,p50_ms(rescore_t[m],calls));
  printf("\"approx_plus_rerank_p50_ms_estimate\": %.6f}%s\n",
         p50_ms(short_t,calls)+p50_ms(rescore_t[m],calls),
         m+1<NC?",":"");
 }
 printf("  ],\n  \"sanity_failures\": %d,\n  \"status\": \"%s\"\n}\n",
        checks,checks?"FAIL":"PASS");
 for(size_t m=0;m<NC;m++)free(rescore_t[m]);
 free(base_t);free(short_t);free(x);free(x8);free(q);free(q8);
 return checks?1:0;
}
