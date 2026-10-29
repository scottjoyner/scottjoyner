// Public, dependency-free, synthetic int8 shortlist + exact float32 reranking benchmark.
// Compile: gcc -O3 -Wall -Wextra -std=c11 bench_rerank.c -lm -o bench_rerank
// Run: ./bench_rerank [vectors=8192] [dimensions=768] [queries=12] [repeats=2] [seed=20261029] [independent|temporal|clustered]
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
static void normalize(float*v,size_t d) {
 double v2=0;
 for(size_t j=0;j<d;j++)v2+=(double)v[j]*v[j];
 double scale=1.0/sqrt(v2);
 for(size_t j=0;j<d;j++)v[j]=(float)(v[j]*scale);
}
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

typedef struct {
 double gap20,gap40,gap80;
 int selected_m, hits_selected, hits_160;
 int hits_at_m[6];
 double scan_ms, rerank_ms, exact_ms, query_ms;
} Sample;
static int choose_m(const Hit*shortlist,double threshold) {
 // Uses only quantized ranks. No distribution label, float32 data or oracle.
 const int sizes[]={20,40,80};
 for(int j=0;j<3;j++) {
  double margin=(shortlist[4].score-shortlist[sizes[j]-1].score)/16129.0;
  if(margin>=threshold) return sizes[j];
 }
 return 160;
}
static int hits5(const Hit*a,const Hit*b) {
 int hits=0;
 for(int i=0;i<K;i++)for(int j=0;j<K;j++)if(a[i].id==b[j].id){hits++;break;}
 return hits;
}
int main(int argc,char**argv){
 size_t n=argc>1?strtoull(argv[1],0,10):8192;
 size_t d=argc>2?strtoull(argv[2],0,10):768;
 size_t nq=argc>3?strtoull(argv[3],0,10):12;
 size_t rep=argc>4?strtoull(argv[4],0,10):2;
 uint64_t seed=argc>5?strtoull(argv[5],0,10):20261029;
 const char*mode=argc>6?argv[6]:"independent";
 double threshold=argc>7?strtod(argv[7],0):0.01;
 if(n<MAX_CANDIDATES||n>150000||d<2||d>4096||nq<1||nq>100
    ||rep<1||rep>10||n>SIZE_MAX/d||nq>SIZE_MAX/d
    ||!isfinite(threshold)||threshold<0||threshold>2
    ||(strcmp(mode,"independent")&&strcmp(mode,"temporal")&&strcmp(mode,"clustered"))){
  fprintf(stderr,"invalid arguments\n");return 2;
 }
 state=seed;
 float*x=malloc(n*d*sizeof(float)),*q=malloc(nq*d*sizeof(float));
 int8_t*x8=malloc(n*d),*q8=malloc(nq*d);
 Sample*samples=calloc(nq,sizeof(Sample));
 long long*t_scan=calloc(nq*rep,sizeof(long long)),*t_end=calloc(nq*rep,sizeof(long long)),
    *t_exact=calloc(nq*rep,sizeof(long long));
 if(!x||!q||!x8||!q8||!samples||!t_scan||!t_end||!t_exact){fprintf(stderr,"allocation failed\n");return 2;}
 for(size_t i=0;i<n;i++){
  float*v=x+i*d;gen(v,d);
  if(!strcmp(mode,"temporal")&&i%256!=0){
   const float*p=x+(i-1)*d;
   for(size_t j=0;j<d;j++)v[j]=.995f*p[j]+.10f*v[j];
   normalize(v,d);
  }else if(!strcmp(mode,"clustered")&&i>=32){
   const float*p=x+(i%32)*d;
   for(size_t j=0;j<d;j++)v[j]=.85f*p[j]+.35f*v[j];
   normalize(v,d);
  }
 }
 for(size_t i=0;i<nq;i++){
  float*v=q+i*d;gen(v,d);
  if(strcmp(mode,"independent")){
   const float*p=x+(rand64()%n)*d;
   for(size_t j=0;j<d;j++)v[j]=.995f*p[j]+.03f*v[j];
   normalize(v,d);
  }
 }
 long long began=ns();
 for(size_t i=0;i<n*d;i++)x8[i]=quant(x[i]);
 for(size_t i=0;i<nq*d;i++)q8[i]=quant(q[i]);
 double prequantize_ms=(ns()-began)/1e6;
 Hit exact5[K],shortlist[MAX_CANDIDATES],chosen5[K],probe[K];
 // Warm both paths before measurements.
 exact(x,q,n,d,exact5);
 approx_candidates(x8,q8,n,d,shortlist);
 int sanity=0,hits=0,fullhits=0;
 int msizes[]={5,10,20,40,80,160};
 for(size_t r=0;r<rep;r++)for(size_t j=0;j<nq;j++){
  size_t idx=r*nq+j;
  const float*query=q+j*d;
  const int8_t*query8=q8+j*d;
  long long t0=ns();exact(x,query,n,d,exact5);
  t_exact[idx]=ns()-t0;
  t0=ns();approx_candidates(x8,query8,n,d,shortlist);
  long long t1=ns();t_scan[idx]=t1-t0;
  int m=choose_m(shortlist,threshold);
  rescore(shortlist,m,x,query,d,chosen5);
  long long t2=ns();t_end[idx]=t2-t0;
  if(!valid(exact5,K,n)||!valid(shortlist,MAX_CANDIDATES,n)||!valid(chosen5,K,n))sanity++;
  if(r==0){
   Sample*s=&samples[j];
   s->gap20=(shortlist[4].score-shortlist[19].score)/16129.0;
   s->gap40=(shortlist[4].score-shortlist[39].score)/16129.0;
   s->gap80=(shortlist[4].score-shortlist[79].score)/16129.0;
   s->selected_m=m;
   s->hits_selected=hits5(exact5,chosen5);
   s->hits_160=0;
   for(int i=0;i<6;i++){
    rescore(shortlist,msizes[i],x,query,d,probe);
    if(!valid(probe,K,n))sanity++;
    s->hits_at_m[i]=hits5(exact5,probe);
   }
   s->hits_160=s->hits_at_m[5];
   s->scan_ms=t_scan[idx]/1e6;
   s->rerank_ms=(t2-t1)/1e6;
   s->query_ms=t_end[idx]/1e6;
   s->exact_ms=t_exact[idx]/1e6;
   hits+=s->hits_selected;
   fullhits+=s->hits_160;
  }
 }
 char host[128]="unknown";gethostname(host,sizeof(host)-1);host[sizeof(host)-1]=0;
 printf("{\n\"schema\":1,\"kind\":\"synthetic_score_margin_adaptive_cpu\","
        "\"host\":\"%s\",\"compiler\":\"%s\",\"distribution\":\"%s\","
        "\"seed\":%llu,\"n\":%zu,\"d\":%zu,\"queries\":%zu,\"repeats\":%zu,"
        "\"threshold\":%.8f,\"prequantize_ms\":%.6f,",host,__VERSION__,mode,
        (unsigned long long)seed,n,d,nq,rep,threshold,prequantize_ms);
 printf("\"adaptive_recall_at5\":%.8f,\"m160_recall_at5\":%.8f,"
        "\"adaptive_median_direct_ms\":%.6f,\"exact_median_ms\":%.6f,"
        "\"int8_scan_median_ms\":%.6f,\"sanity_failures\":%d,"
        "\"status\":\"%s\",\"query_details\":[",
        (double)hits/(K*nq),(double)fullhits/(K*nq),
        p50_ms(t_end,nq*rep),p50_ms(t_exact,nq*rep),p50_ms(t_scan,nq*rep),
        sanity,sanity?"FAIL":"PASS");
 for(size_t j=0;j<nq;j++){
  Sample*s=&samples[j];
  printf("%s{\"q\":%zu,\"gap20\":%.8f,\"gap40\":%.8f,\"gap80\":%.8f,"
         "\"selected_m\":%d,\"hits_selected\":%d,\"hits_160\":%d,"
         "\"hits_by_m\":[%d,%d,%d,%d,%d,%d],"
         "\"query_ms\":%.6f,\"scan_ms\":%.6f,\"rerank_ms\":%.6f,\"exact_ms\":%.6f}",
         j?",":"",j,s->gap20,s->gap40,s->gap80,s->selected_m,
         s->hits_selected,s->hits_160,
         s->hits_at_m[0],s->hits_at_m[1],s->hits_at_m[2],
         s->hits_at_m[3],s->hits_at_m[4],s->hits_at_m[5],
         s->query_ms,s->scan_ms,s->rerank_ms,s->exact_ms);
 }
 printf("]}\n");
 free(x);free(q);free(x8);free(q8);free(samples);free(t_scan);free(t_end);free(t_exact);
 return sanity?1:0;
}
