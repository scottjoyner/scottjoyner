// Bounded read-only shared-index Unix-socket CPU retrieval service for synthetic benchmarks.
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
#include <pthread.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <arpa/inet.h>
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

#define CAP 32
typedef struct { uint32_t status,hits; uint64_t queue_ns,compute_ns; } Response;
_Static_assert(sizeof(Response)==24,"Binary response must be 24 bytes");
typedef struct { int fd;long long enter_ns; } Request;
static struct {
 float *x,*q,*scales;int8_t*x8,*q8;Hit *truth;
 size_t n,d,nq;int file_fd,m,mode,workers,qlimit;
 Request slots[CAP];int head,tail,len;pthread_mutex_t mu;pthread_cond_t cv;
} S={.file_fd=-1,.mu=PTHREAD_MUTEX_INITIALIZER,.cv=PTHREAD_COND_INITIALIZER};
static int io_read(int fd,void*buf,size_t len){
 char*b=buf;
 while(len){ssize_t z=read(fd,b,len);if(z<0){if(errno==EINTR)continue;return -1;}if(!z)return -1;b+=z;len-=z;}
 return 0;
}
static void send_response(int fd,const Response*r){
 const char*data=(const char*)r;size_t len=sizeof(*r);
 while(len){
  ssize_t n=send(fd,data,len,MSG_NOSIGNAL);
  if(n<0){if(errno==EINTR)continue;break;}
  if(n==0)break;
  data+=n;len-=(size_t)n;
 }
}
static void *worker(void *unused){
 (void)unused;
 float*buf=malloc((size_t)S.m*S.d*sizeof(float));
 if(!buf){fprintf(stderr,"worker buffer allocation failed\n");return NULL;}
 for(;;){
  pthread_mutex_lock(&S.mu);
  while(S.len==0)pthread_cond_wait(&S.cv,&S.mu);
  Request r=S.slots[S.head];S.head=(S.head+1)%CAP;S.len--;
  pthread_mutex_unlock(&S.mu);
  uint64_t queue_ns=(uint64_t)(now_ns()-r.enter_ns);
  long long began=now_ns();
  uint32_t req=UINT32_MAX;
  Response out={.status=2,.hits=0,.queue_ns=queue_ns};
  if(io_read(r.fd,&req,sizeof(req))==0 && req<S.nq){
   Hit shortlist_hits[MAXM], answer[K];
   const float*query=S.q+(size_t)req*S.d;
   shortlist(S.x8,S.scales,S.q8+(size_t)req*S.d,S.n,S.d,S.m,shortlist_hits);
   init(answer,K);
   int failed=0;
   if(S.mode==0){
    for(int j=0;j<S.m;j++){
     size_t id=shortlist_hits[j].id;
     add(answer,K,dot32(S.x+id*S.d,query,S.d),id);
    }
   }else if(S.mode==1){
    for(int j=0;j<S.m;j++){
     size_t id=shortlist_hits[j].id;
     if(pread_all(S.file_fd,buf,S.d*sizeof(float),(off_t)(id*S.d*sizeof(float)))<0){failed=1;break;}
     add(answer,K,dot32(buf,query,S.d),id);
    }
   }else{
    size_t ids[MAXM];
    for(int j=0;j<S.m;j++)ids[j]=shortlist_hits[j].id;
    qsort(ids,S.m,sizeof(size_t),cmp_size);
    for(int j=0;j<S.m;){
     int end=j+1;
     while(end<S.m && ids[end]==ids[end-1]+1)end++;
     size_t count=(size_t)(end-j);
     if(pread_all(S.file_fd,buf,count*S.d*sizeof(float),
          (off_t)(ids[j]*S.d*sizeof(float)))<0){failed=1;break;}
     for(int k=j;k<end;k++)add(answer,K,dot32(buf+(size_t)(k-j)*S.d,query,S.d),ids[k]);
     j=end;
    }
   }
   if(!failed&&valid(answer,K,S.n)){
    out.status=0;out.hits=(uint32_t)count_hits(S.truth+(size_t)req*K,answer);
   }else out.status=3;
  }
  out.compute_ns=(uint64_t)(now_ns()-began);
  send_response(r.fd,&out);close(r.fd);
 }
 return NULL;
}
int main(int argc,char**argv){
 if(argc!=10){
  fprintf(stderr,"usage: %s socket n d nqueries seed independent|temporal|clustered ram|rank|coalesced workers queue_limit\n",argv[0]);return 2;
 }
 const char*sock=argv[1];S.n=strtoull(argv[2],NULL,10);S.d=strtoull(argv[3],NULL,10);
 S.nq=strtoull(argv[4],NULL,10);uint64_t seed=strtoull(argv[5],NULL,10);
 const char*dist=argv[6];const char*mode=argv[7];
 S.workers=atoi(argv[8]);S.qlimit=atoi(argv[9]);S.m=160;
 if(strlen(sock)>=sizeof(((struct sockaddr_un*)0)->sun_path)||
   S.n<160||S.n>65536||S.d<2||S.d>1536||S.nq<1||S.nq>32||
   S.workers<1||S.workers>8||S.qlimit<1||S.qlimit>CAP||
   S.n>SIZE_MAX/S.d||S.n*S.d>SIZE_MAX/sizeof(float)||
   (strcmp(dist,"independent")&&strcmp(dist,"temporal")&&strcmp(dist,"clustered"))||
   (strcmp(mode,"ram")&&strcmp(mode,"rank")&&strcmp(mode,"coalesced"))){
  fprintf(stderr,"invalid bounded server config\n");return 2;
 }
 S.mode=!strcmp(mode,"ram")?0:!strcmp(mode,"rank")?1:2;
 signal(SIGPIPE,SIG_IGN);seed_state=seed;
 size_t bytes=S.n*S.d*sizeof(float);
 float*x=malloc(bytes);S.q=malloc(S.nq*S.d*sizeof(float));
 S.x8=malloc(S.n*S.d);S.q8=malloc(S.nq*S.d);
 S.scales=malloc(S.n*sizeof(float));S.truth=calloc(S.nq*K,sizeof(Hit));
 if(!x||!S.q||!S.x8||!S.q8||!S.scales||!S.truth)return bad("shared index malloc");
 for(size_t i=0;i<S.n;i++){
  float*v=x+i*S.d;gen(v,S.d);
  if(!strcmp(dist,"temporal")&&i%256!=0){
   const float*p=x+(i-1)*S.d;
   for(size_t j=0;j<S.d;j++)v[j]=.995f*p[j]+.10f*v[j];
   normalize(v,S.d);
  }else if(!strcmp(dist,"clustered")&&i>=32){
   const float*p=x+(i%32)*S.d;
   for(size_t j=0;j<S.d;j++)v[j]=.85f*p[j]+.35f*v[j];
   normalize(v,S.d);
  }
 }
 for(size_t i=0;i<S.nq;i++){
  float*v=S.q+i*S.d;gen(v,S.d);
  if(strcmp(dist,"independent")){
   const float*p=x+(r64()%S.n)*S.d;
   for(size_t j=0;j<S.d;j++)v[j]=.995f*p[j]+.03f*v[j];
   normalize(v,S.d);
  }
  exact(x,v,S.n,S.d,S.truth+i*K);
 }
 for(size_t i=0;i<S.n;i++){
  float z=scale_for(x+i*S.d,S.d);S.scales[i]=z;
  for(size_t j=0;j<S.d;j++)S.x8[i*S.d+j]=quant(x[i*S.d+j],z);
 }
 for(size_t i=0;i<S.nq;i++){
  float z=scale_for(S.q+i*S.d,S.d);
  for(size_t j=0;j<S.d;j++)S.q8[i*S.d+j]=quant(S.q[i*S.d+j],z);
 }
 if(S.mode==0)S.x=x;
 else {
  char name[]="/tmp/bench-sensorgraft-shared-XXXXXX";
  S.file_fd=mkstemp(name);
  if(S.file_fd<0)return bad("mkstemp");
  if(unlink(name)<0||write_all(S.file_fd,x,bytes)<0)return bad("anonymous synthetic backing");
  free(x);S.x=NULL;
 }
 int fd=socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);if(fd<0)return bad("Unix socket");
 struct sockaddr_un addr={.sun_family=AF_UNIX};
 strncpy(addr.sun_path,sock,sizeof(addr.sun_path)-1);
 if(bind(fd,(struct sockaddr*)&addr,sizeof(addr))<0)return bad("bind");
 if(chmod(sock,0600)<0)return bad("socket permissions");
 if(listen(fd,128)<0)return bad("listen");
 for(int i=0;i<S.workers;i++){
  pthread_t tid;
  if(pthread_create(&tid,NULL,worker,NULL)!=0)return bad("pthread_create");
  pthread_detach(tid);
 }
 printf("READY rss_kib=%ld n=%zu d=%zu mode=%s threads=%d queue=%d\n",
         rss_kib(),S.n,S.d,mode,S.workers,S.qlimit);
 fflush(stdout);
 for(;;){
  int client=accept4(fd,NULL,NULL,SOCK_CLOEXEC);
  if(client<0){if(errno==EINTR)continue;return bad("accept");}
  long long entered=now_ns();
  pthread_mutex_lock(&S.mu);
  if(S.len>=S.qlimit){
   pthread_mutex_unlock(&S.mu);
   Response busy={.status=1};
   send_response(client,&busy);close(client);
  }else{
   S.slots[S.tail]=(Request){.fd=client,.enter_ns=entered};
   S.tail=(S.tail+1)%CAP;S.len++;
   pthread_cond_signal(&S.cv);
   pthread_mutex_unlock(&S.mu);
  }
 }
}
