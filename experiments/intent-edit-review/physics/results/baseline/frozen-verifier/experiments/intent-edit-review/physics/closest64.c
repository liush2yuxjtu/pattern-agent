/* Closest-feature arithmetic in f64. Body/cloth storage remains original f32.
 * Thin decimated fingertip triangles lose micrometres in f32 Gram determinants.
 */
typedef struct {double x,y,z;} DV;
static DV diff64(V a,V b){return (DV){(double)a.x-b.x,(double)a.y-b.y,(double)a.z-b.z};}
static double dot64(DV a,DV b){return a.x*b.x+a.y*b.y+a.z*b.z;}
static V foot64(V a,DV ab,DV ac,double u,double v){return (V){a.x+ab.x*u+ac.x*v,a.y+ab.y*u+ac.y*v,a.z+ab.z*u+ac.z*v};}
static V closest(V p,V a,V b,V c,float *u,float *v){
 DV ab=diff64(b,a),ac=diff64(c,a),ap=diff64(p,a);double d1=dot64(ab,ap),d2=dot64(ac,ap);
 if(d1<=0&&d2<=0){*u=*v=0;return a;}
 DV bp=diff64(p,b);double d3=dot64(ab,bp),d4=dot64(ac,bp);
 if(d3>=0&&d4<=d3){*u=1;*v=0;return b;}
 double vc=d1*d4-d3*d2;
 if(vc<=0&&d1>=0&&d3<=0){double t=d1/(d1-d3);*u=t;*v=0;return foot64(a,ab,ac,t,0);}
 DV cp=diff64(p,c);double d5=dot64(ab,cp),d6=dot64(ac,cp);
 if(d6>=0&&d5<=d6){*u=0;*v=1;return c;}
 double vb=d5*d2-d1*d6;
 if(vb<=0&&d2>=0&&d6<=0){double t=d2/(d2-d6);*u=0;*v=t;return foot64(a,ab,ac,0,t);}
 double va=d3*d6-d5*d4;
 if(va<=0&&d4-d3>=0&&d5-d6>=0){double t=(d4-d3)/((d4-d3)+(d5-d6));*u=1-t;*v=t;return foot64(a,ab,ac,1-t,t);}
 double den=va+vb+vc,bu=vb/den,bv=vc/den;*u=bu;*v=bv;return foot64(a,ab,ac,bu,bv);
}
