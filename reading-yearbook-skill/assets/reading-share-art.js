/* Editorial share artwork. Data-driven layouts; no external requests.
 * Chart encodings reuse the yearbook's lieflat line / rung / tick vocabulary.
 * Each canvas carries a local layout manifest for export regression checks. */
window.ReadingShareArtwork = (() => {
  'use strict';
  const C={paper:'#fffdf6',ink:'#30271f',muted:'#735c4b',secondaryInk:'#554333',quietBlue:'#205ac5',red:'#b83225',blue:'#205ac5',gold:'#d5a126',green:'#167c70',line:'#e8cfab',cream:'#fff1d4'};
  const SERIF='ReadingSerif,"Noto Serif SC","Songti SC",SimSun,serif';
  const SANS='ReadingSans,"Noto Sans SC","Microsoft YaHei",sans-serif';
  const NUM='Georgia,"Noto Serif",serif';
  const palette=[C.blue,C.red,C.green,C.gold,'#97768b','#7a8875','#bd8261'];
  const known=n=>typeof n==='number'&&Number.isFinite(n);
  const amount=n=>known(n)?String(n):'—';
  const duration=n=>!known(n)?'未记录':n>=3600?`${Math.floor(n/3600)}小时${Math.floor(n%3600/60)}分钟`:`${Math.floor(n/60)}分钟`;
  const status=b=>({finished:'已读完',reading:'在读',unstarted:'未开始',unknown:'状态未记录'}[b.status]??(b.progress==null?'进度未记录':b.progress>=100?'已读完':'在读'));
  function create({data,art,loadImage}){
    const fonts=Promise.all([document.fonts.load('600 48px ReadingSerif'),document.fonts.load('400 32px ReadingSerif'),document.fonts.load('400 28px ReadingSans')]);
    const categories=new Map();for(const b of data.books)categories.set(b.category,(categories.get(b.category)||0)+1);
    const counts=[...categories].map(([name,count])=>({name,count})).sort((a,b)=>b.count-a.count||a.name.localeCompare(b.name,'zh'));
    const colors=new Map(counts.map((r,i)=>[r.name,palette[i%palette.length]]));
    const chartPalette=['#bd5143','#4477a1','#b8973b','#5c897c','#ac7b84','#897b9e','#71828b'];
    const chartColors=new Map([...categories].sort((a,b)=>b[1]-a[1]).map(([name],i)=>[name,chartPalette[i%chartPalette.length]]));
    const bookAccents=new Map(),bookColor=b=>bookAccents.get(b.book_id)||colors.get(b.category)||C.blue;
    async function coverAccent(b){
      if(!b.cover||bookAccents.has(b.book_id))return;
      const im=await loadImage(b.cover).catch(()=>null);
      if(!im)return;
      const cv=document.createElement('canvas');cv.width=cv.height=24;const c=cv.getContext('2d');c.drawImage(im,0,0,24,24);
      // Quantize colored cover pixels into legible ink hues. White / neutral paper
      // has no vote, and category-chart colors keep their own stable semantics.
      const inks=[C.red,C.blue,C.green,'#8a6825','#79596d','#675b40'],rgb=inks.map(h=>[1,3,5].map(i=>parseInt(h.slice(i,i+2),16))),votes=inks.map(()=>0),pixels=c.getImageData(0,0,24,24).data;
      for(let i=0;i<pixels.length;i+=4){const p=[pixels[i],pixels[i+1],pixels[i+2]],sat=Math.max(...p)-Math.min(...p);if(pixels[i+3]<180||sat<35||Math.min(...p)>210)continue;let best=0,dist=Infinity;rgb.forEach((r,k)=>{const v=r.reduce((s,a,j)=>s+(a-p[j])**2,0);if(v<dist){best=k;dist=v;}});votes[best]+=sat;}
      if(Math.max(...votes)>0)bookAccents.set(b.book_id,inks[votes.indexOf(Math.max(...votes))]);
    }
    const events=[],seenEvents=new Set();for(const b of data.books){
      if(b.start_date?.startsWith(String(data.year)))events.push({date:b.start_date.slice(0,10),type:'开始阅读',book:b});
      if(b.finish_date?.startsWith(String(data.year)))events.push({date:b.finish_date.slice(0,10),type:'读完',book:b});
      for(const [kind,rows]of [['划线',b.highlights],['笔记',b.thoughts]])for(const n of rows)if(n.created_at?.startsWith(String(data.year))){const key=`${b.book_id}|${kind}|${n.source_id||n.text+'|'+n.created_at}`;if(!seenEvents.has(key)){seenEvents.add(key);events.push({date:n.created_at.slice(0,10),type:kind,book:b});}}
    }
    events.sort((a,b)=>a.date.localeCompare(b.date)||a.book.book_id.localeCompare(b.book.book_id));
    const months=data.summary.monthly.slice(0,data.summary.complete_months);
    function drawing(cv,p){
      const ctx=cv.getContext('2d'),W=cv.width,H=cv.height,M=64,R=W-M;
      const manifest={version:'editorial-2',page:p.id,width:W,height:H,footerTop:H-84,text:[],charts:[],images:[],spacing:[],blocks:[]};cv.readingLayout=manifest;
      function text(str,x,y,{size=30,weight=400,font=SERIF,color=C.ink,align='left',italic=false,role='content'}={}){
        ctx.font=`${italic?'italic ':''}${weight} ${size}px ${font}`;ctx.fillStyle=color;ctx.textAlign=align;ctx.textBaseline='alphabetic';
        ctx.fillText(String(str),x,y);const metric=ctx.measureText(String(str));
        const box={text:String(str),x:x-metric.actualBoundingBoxLeft,y:y-metric.actualBoundingBoxAscent,w:metric.actualBoundingBoxLeft+metric.actualBoundingBoxRight,h:metric.actualBoundingBoxAscent+metric.actualBoundingBoxDescent,size,role};
        if(String(str).trim())manifest.text.push(box);ctx.textAlign='left';return box;
      }
      function lines(str,width,style){
        ctx.font=`${style.weight||400} ${style.size||30}px ${style.font||SERIF}`;const out=[];let line='';
        for(const ch of String(str).replace(/\r/g,'')){
          if(ch==='\n'){out.push(line);line='';continue;}
          if(ctx.measureText(line+ch).width>width&&line){
            if(/[，。！？；：、）》】”’]/.test(ch)){out.push(line.slice(0,-1));line=line.slice(-1)+ch;}
            else if(/[（《【“‘]$/.test(line)){out.push(line.slice(0,-1));line=line.slice(-1)+ch;}
            else{out.push(line);line=ch;}
          }else line+=ch;
        }if(line)out.push(line);return out;
      }
      function measureBlock(str,w,h,{size=36,min=32,weight=400,font=SERIF,leading=1.5}={}){
        let ls=[],descent=0;
        while(size>=min){ls=lines(str,w-8,{size,weight,font});ctx.font=`${weight} ${size}px ${font}`;descent=ctx.measureText('阅读Ag，。').actualBoundingBoxDescent;
          if((ls.length-1)*size*leading+size+descent<=h||size===min)break;size=Math.max(min,size-2);}
        const step=size*leading,max=Math.max(0,1+Math.floor((h-size-descent)/step)),cut=ls.length>max;ls=ls.slice(0,max);
        if(cut&&ls.length){let last=ls.at(-1);ctx.font=`${weight} ${size}px ${font}`;while(last&&ctx.measureText(last+'…').width>w-8)last=last.slice(0,-1);ls[ls.length-1]=last+'…';}
        return {rows:ls,size,step,cut,height:ls.length?size+(ls.length-1)*step+descent:0};
      }
      function block(str,x,y,w,h,style={}){
        const fit=measureBlock(str,w,h,style);if(!fit.rows.length)return {bottom:y,lines:0,cut:Boolean(str)};
        fit.rows.forEach((s,i)=>text(s,x,y+fit.size+i*fit.step,{...style,size:fit.size}));
        manifest.blocks.push({x,y,w,h,cut:fit.cut});return {bottom:y+fit.height,lines:fit.rows.length,cut:fit.cut};
      }
      function rect(x,y,w,h,fill,stroke){ctx.fillStyle=fill;ctx.fillRect(x,y,w,h);if(stroke){ctx.strokeStyle=stroke;ctx.lineWidth=1;ctx.strokeRect(x,y,w,h);}}
      function line(x1,y1,x2,y2,color=C.line,width=1){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();}
      function dot(x,y,r,color){ctx.fillStyle=color;ctx.beginPath();ctx.arc(x,y,r,0,Math.PI*2);ctx.fill();}
      function section(label,x,y,w,no){line(x,y-12,x+w,y-12);text(no||'',x,y+22,{font:NUM,size:25,color:C.red,italic:true});text(label,x+(no?45:0),y+22,{size:27,weight:500,font:SANS});return y+48;}
      function scribble(x,y,w,color=C.red){ctx.strokeStyle=color;ctx.lineWidth=2;ctx.beginPath();for(let i=0;i<=30;i++){const xx=x+w*i/30,yy=y+Math.sin(i*.85)*1.5+i*.05;i?ctx.lineTo(xx,yy):ctx.moveTo(xx,yy);}ctx.stroke();}
      function star(x,y,r,color=C.gold){for(let i=0;i<4;i++){const a=i*Math.PI/4;line(x-Math.cos(a)*r,y-Math.sin(a)*r,x+Math.cos(a)*r,y+Math.sin(a)*r,color,1.5);}}
      async function image(src,x,y,w,h,{angle=0,shadow=false,fit='contain'}={}){
        const im=await loadImage(src),s=fit==='contain'?Math.min(w/im.width,h/im.height):Math.max(w/im.width,h/im.height),iw=im.width*s,ih=im.height*s;
        ctx.save();ctx.translate(x+w/2,y+h/2);ctx.rotate(angle*Math.PI/180);if(shadow){ctx.shadowColor='#31312630';ctx.shadowBlur=16;ctx.shadowOffsetX=5;ctx.shadowOffsetY=10;}
        if(fit==='cover'){ctx.beginPath();ctx.rect(-w/2,-h/2,w,h);ctx.clip();}ctx.drawImage(im,-iw/2,-ih/2,iw,ih);ctx.restore();
        const rad=angle*Math.PI/180,bw=Math.abs(iw*Math.cos(rad))+Math.abs(ih*Math.sin(rad)),bh=Math.abs(iw*Math.sin(rad))+Math.abs(ih*Math.cos(rad));
        manifest.images.push({x:x+w/2-bw/2,y:y+h/2-bh/2,w:bw,h:bh,angle});
      }
      async function cover(b,x,y,w,h,opts={}){
        if(b.cover){
          try{await image(b.cover,x,y,w,h,opts);return;}catch{/* Render the same placeholder as a missing cover. */}
        }
        rect(x,y,w,h,C.cream,C.line);
        rect(x,y,Math.min(5,w/5),h,C.gold);
        if(w>=70&&h>=72){
          const inset=w<120?10:17;
          block(b.title,x+inset,y+inset,w-inset*2,h-inset*2,{
            size:w<120?21:30,min:w<120?16:23,weight:600,leading:1.25
          });
        }
      }
      function metric(n,label,x,y,w,{size=64,color=C.ink,labelY,labelSize=26}={}){
        const s=amount(n);let fs=size;ctx.font=`400 ${fs}px ${NUM}`;while(ctx.measureText(s).width>w-8&&fs>28){fs-=2;ctx.font=`400 ${fs}px ${NUM}`;}
        const numberBox=text(s,x,y,{size:fs,font:NUM,color});
        // Labels in a row share a baseline, even when a long value shrinks.
        ctx.font=`400 ${size}px ${NUM}`;const descent=ctx.measureText('0123456789').actualBoundingBoxDescent;
        ctx.font=`400 ${labelSize}px ${SANS}`;const ascent=ctx.measureText('阅读小时分钟').actualBoundingBoxAscent;
        const labelBox=text(label,x,labelY??y+descent+ascent+18,{size:labelSize,font:SANS,color:C.muted});
        manifest.spacing.push({kind:'metric',gap:labelBox.y-numberBox.y-numberBox.h,minimum:14,labelY:labelBox.y+labelBox.h});
      }
      function progress(b,x,y,w){
        if(!known(b.progress))return;const v=Math.max(0,Math.min(100,b.progress));text('当前进度',x,y,{size:26,font:SANS,color:C.muted});text(`${v}%`,x+w,y,{size:30,font:NUM,align:'right',color:bookColor(b)});
        rect(x,y+18,w,8,C.cream);rect(x,y+18,w*v/100,8,bookColor(b));manifest.charts.push({kind:'progress',value:v,width:w*v/100,totalWidth:w});
      }
      function trend(x,y,w,h,{small=false}={}){
        const vals=months,valid=vals.map((v,i)=>({v,i})).filter(r=>known(r.v));
        if(!valid.length){
          if(small)text('月度时长未记录',x,y+h/2+10,{size:25,font:SANS,color:C.muted});
          else block('暂无月度阅读时长记录。',x,y+35,w,h-35,{size:32,min:30,color:C.muted});
          return;
        }
        const top=Math.ceil(Math.max(...valid.map(r=>r.v/3600),1)/2)*2,left=x+(small?8:42),right=x+w-16,base=y+h-44,upper=y+26;
        if(!small)for(const v of [0,top/2,top]){const yy=base-v/top*(base-upper);line(left,yy,right,yy);text(String(v),x,yy+8,{size:25,font:NUM,color:C.muted});}
        const points=vals.map((v,i)=>known(v)?{value:v,month:i+1,x:vals.length===1?(left+right)/2:left+i*(right-left)/(vals.length-1),y:base-v/3600/top*(base-upper)}:null);
        ctx.strokeStyle=C.red;ctx.lineWidth=small?2:3;ctx.beginPath();let active=false;for(const pt of points){if(!pt){active=false;continue;}active?ctx.lineTo(pt.x,pt.y):ctx.moveTo(pt.x,pt.y);active=true;}ctx.stroke();
        const peak=valid.reduce((a,b)=>b.v>a.v?b:a);for(const pt of points)if(pt)dot(pt.x,pt.y,small?3:5,pt.month===peak.i+1?C.blue:C.red);
        if(!small){for(let i=0;i<vals.length;i++){const xx=vals.length===1?(left+right)/2:left+i*(right-left)/(vals.length-1);if(vals.length<=9||i%2===0||i===vals.length-1)text(`${i+1}月`,xx,base+35,{size:25,font:SANS,color:C.muted,align:'center'});}text('小时',x,y+5,{size:23,font:SANS,color:C.muted});}
        manifest.charts.push({kind:'monthly',points,top,base,upper});
      }
      function base(){
        rect(0,0,W,H,C.paper);
        let seed=281;ctx.fillStyle='#635237';ctx.globalAlpha=.045;for(let i=0;i<3600;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;const x=seed%W;seed=(Math.imul(seed,1664525)+1013904223)>>>0;ctx.fillRect(x,seed%H,1,1);}ctx.globalAlpha=1;
        ctx.strokeStyle=C.line;ctx.lineWidth=1;ctx.strokeRect(22,22,W-44,H-44);
        rect(22,22,48,3,C.red);rect(W-70,H-25,48,3,C.gold);
        text('年年阅',M,72,{size:28,weight:600});
        const labels={cover:'阅读年鉴',stats:'阅读的节奏',distribution:'阅读分布',timeline:'阅读时间线',book:'书页之间'};
        text(labels[p.kind],W/2,71,{font:SANS,size:24,align:'center',color:C.muted});text(`${data.year}${data.source_mode==='sample'?' · 示例':''}`,R,72,{font:NUM,size:27,align:'right'});line(M,95,R,95);
        const idx=p.kind==='book'?5+data.books.findIndex(b=>b.book_id===p.book.book_id):['cover','stats','distribution','timeline'].indexOf(p.kind)+1;
        line(M,H-84,R,H-84);
        text(`${String(idx).padStart(2,'0')} / ${String(4+data.books.length).padStart(2,'0')}`,M,H-44,{font:NUM,size:24,color:C.muted,role:'footer'});
        text(p.kind==='book'?(p.quote?(p.textKind==='thought'?'个人笔记与阅读记录':'原文摘录与阅读记录'):'阅读记录'):'我的阅读年鉴',R,H-44,{size:23,font:SANS,align:'right',color:C.muted,role:'footer'});
      }
      return {ctx,W,H,M,R,text,block,measureBlock,rect,line,dot,section,scribble,star,image,cover,metric,progress,trend,base,manifest};
    }
    async function render(p,ratio){
      await fonts;await document.fonts.ready;const cv=document.createElement('canvas');cv.width=900;cv.height=ratio==='1:1'?900:ratio==='4:5'?1125:1200;
      const D=drawing(cv,p);if(!D.ctx)throw Error('浏览器不支持Canvas');D.base();
      if(p.kind==='cover')await coverPage(D);
      else if(p.kind==='stats')await statsPage(D);
      else if(p.kind==='distribution')await distributionPage(D);
      else if(p.kind==='timeline')await timelinePage(D);
      else{await coverAccent(p.book);await bookPage(D,p);}
      return cv;
    }
    function calendar(d,x,y,width){
      const daily=data.features?.daily??{};
      const day=86400000,start=Date.UTC(data.year,0,1),end=Date.UTC(data.year+1,0,1);
      const cutoff=data.as_of?Date.parse(data.as_of):end-day;
      const offset=(new Date(start).getUTCDay()+6)%7;
      const weeks=Math.ceil(((end-start)/day+offset)/7);
      const pitch=Math.min(14,width/weeks),size=pitch-2;
      const colors=['#efe4d4','#efcf9b','#dda366','#bf6246','#923a30'];
      const keys=Object.keys(daily);
      d.text('每天的阅读记录',x,y,{font:SANS,size:24,weight:500});
      if(!keys.length){
        d.text('本次未取得逐日时长',x,y+62,{font:SANS,size:27,color:C.muted});
        return;
      }
      const gridY=y+48;
      for(let time=start;time<end;time+=day){
        const date=new Date(time),index=(time-start)/day+offset;
        const left=x+Math.floor(index/7)*pitch,top=gridY+(index%7)*pitch;
        const value=daily[date.toISOString().slice(0,10)];
        if(date.getUTCDate()===1 && date.getUTCMonth()%2===0){
          d.text((date.getUTCMonth()+1)+'月',left,y+37,{font:SANS,size:17,color:C.muted});
        }
        if(time>cutoff)continue;
        if(!known(value))d.rect(left+.5,top+.5,size-1,size-1,C.paper,'#eadcc7');
        else d.rect(left,top,size,size,colors[value===0?0:value<=900?1:value<=1800?2:value<=3600?3:4]);
      }
      const legendY=gridY+7*pitch+22;
      d.rect(x,legendY-12,12,12,C.paper,'#eadcc7');
      d.text('缺记录',x+21,legendY,{font:SANS,size:18,color:C.muted});
      d.text('空白为未到日期',x+116,legendY,{font:SANS,size:18,color:C.muted});
      d.text('0分钟',x+475,legendY,{font:SANS,size:18,color:C.muted});
      colors.forEach((fill,i)=>d.rect(x+540+i*19,legendY-13,14,14,fill));
      d.text('超过60分钟',x+645,legendY,{font:SANS,size:18,color:C.muted});
      d.manifest.charts.push({kind:'calendar',weeks,days:keys.length});
    }
    async function coverPage(d){
      const {H,M,R,text,block,line,image,cover,metric,star}=d,square=H===900;
      const titleY=square?230:302, shelfTop=square?290:395, shelfBottom=square?477:H-468;
      text(String(data.year),M,square?188:221,{font:NUM,size:square?94:121,color:C.red,italic:true});
      await image(art.reading,575,120,247,118);
      text(data.books.length?'这一年，读了这些书':'这一年的阅读年鉴',M,titleY+34,{size:square?56:61,weight:600});
      d.scribble(M,titleY+53,363,C.blue);star(800,titleY+19,13);
      const chosen=[...data.books.filter(b=>b.selected),...data.books.filter(b=>!b.selected)].slice(0,5);
      if(chosen.length){
        const cw=square?139:167,gap=cw*.83,total=cw+(chosen.length-1)*gap,left=(900-total)/2;
        for(const [i,b]of chosen.entries())await cover(b,left+i*gap,shelfTop+(i%2?9:0),cw,shelfBottom-shelfTop-18,{angle:[-4,3,-2,4,-3][i],shadow:true});
      }else{
        if(art.emptyShelf)await image(art.emptyShelf,M,shelfTop-10,R-M,shelfBottom-shelfTop-39);
        block(data.coverage.complete?'这一年还没有阅读记录。':'本次未取得书目。',M,shelfBottom-48,R-M,46,{size:27,min:25,color:C.muted});
      }
      line(M,shelfBottom+8,R,shelfBottom+8);
      const metrics=[[data.summary.read,'本读过'],[data.summary.finished,'本读完'],[data.summary.read_days,'天阅读'],[data.summary.notes,'条笔记']];
      for(const [i,[value,label]]of metrics.entries())metric(value,label,M+i*193,shelfBottom+70,169,{size:48,labelSize:21});
      text(duration(data.summary.seconds),R,H-288,{font:SANS,size:23,align:'right',color:C.quietBlue});
      calendar(d,M,H-288,R-M);
    }
    async function statsPage(d){
      const {H,M,R,text,rect,trend,section}=d,square=H===900;
      text('阅读的节奏',M,174,{size:56,weight:600});
      section('每月阅读时长',M,227,R-M,'01');
      trend(M,285,R-M,square?187:275);
      const valid=months.map((v,i)=>({v,i})).filter(row=>known(row.v));
      const peak=valid.length?valid.reduce((a,b)=>b.v>a.v?b:a):null;
      const durations=Object.values(data.features?.daily??{}).filter(value=>known(value)&&value>0);
      const sparse=durations.length<12||data.books.length<=3;
      const split=(square?531:668)+(sparse?(square?12:40):0);
      const peakY=square?493:597;
      if(peak?.v>0)text(peak.i+1+'月读得最久 · '+duration(peak.v),M,peakY,{font:SANS,size:22,color:C.quietBlue});
      section('单日阅读时长分布',M,split,R-M,'02');
      if(!durations.length){
        text('暂无可统计的正时长日记录',M,split+105,{font:SANS,size:28,color:C.muted});
        const {seconds,read_days:days}=data.summary;
        if(known(seconds)&&days>0)text('按年度汇总，阅读日平均 '+duration(seconds/days),M,split+160,{font:SANS,size:24,color:C.muted});
        return;
      }
      const bins=[['15分钟以内',900],['15至30分钟',1800],['30至60分钟',3600],['超过60分钟',Infinity]]
        .map(([label,max],i,all)=>({label,count:durations.filter(value=>value<=max&&value>(all[i-1]?.[1]??0)).length}));
      const max=Math.max(...bins.map(row=>row.count));
      const firstRow=split+(sparse?(square?73:85):(square?68:78));
      const stride=(H-139-firstRow)/4;
      for(const [i,row]of bins.entries()){
        const y=firstRow+i*stride;
        text(row.label,M,y,{font:SANS,size:24});
        rect(M+228,y-19,444,16,C.cream);
        rect(M+228,y-19,444*row.count/max,16,['#efcf9b','#dda366','#bf6246','#923a30'][i]);
        text(row.count+'天',R,y,{font:SANS,size:23,color:C.muted,align:'right'});
      }
      text('按有正时长记录的'+durations.length+'天统计',M,firstRow+4*stride,{font:SANS,size:21,color:C.muted});
      d.manifest.charts.push({kind:'day-distribution',bins,total:durations.length});
    }
    async function distributionPage(d){
      const {H,M,R,text,block,rect,section,cover}=d,square=H===900;
      text('今年，读向了哪些地方',M,176,{size:54,weight:600});
      d.metric(data.books.length,'本书',M,265,200,{size:64,color:C.red});
      text(counts.length+'个分类',R,268,{font:SANS,size:28,color:C.muted,align:'right'});
      if(!counts.length){
        block(data.coverage.complete?'这一年还没有书目可供分类。':'本次未取得可分类的书目。',M,356,R-M,70,{size:33,min:30});
        if(art.emptyShelf)await d.image(art.emptyShelf,M+34,463,R-M-68,H-603);
        return;
      }
      const limit=square?6:8,retained=counts.slice(0,counts.length>limit?limit-1:limit);
      const omitted=counts.length-retained.length;
      const rows=omitted?[...retained,{name:'其他'+omitted+'类',count:counts.slice(retained.length).reduce((n,r)=>n+r.count,0),other:true}]:retained;
      const sparse=rows.length<=3;
      const sectionY=square?(sparse?378:359):(sparse?410:376);
      section('按书目数量统计',M,sectionY,R-M,'01');
      const firstRow=sectionY+(sparse?(square?72:84):70);
      const lastRow=rows.length===1?firstRow:sparse?(square?610:730):H-(omitted?171:160);
      const stride=rows.length>1?(lastRow-firstRow)/(rows.length-1):0;
      for(const [i,row]of rows.entries()){
        const y=firstRow+i*stride,pct=row.count/data.books.length;
        block(row.name,M,y-28,R-M-168,39,{size:26,min:24,font:SANS});
        text(row.count+'本 · '+Math.round(pct*100)+'%',R,y,{font:SANS,size:23,align:'right',color:C.muted});
        rect(M,y+14,R-M,11,C.cream);
        rect(M,y+14,(R-M)*pct,11,row.other?'#a79786':chartColors.get(row.name)||C.red);
      }
      if(omitted)text('其余分类合并统计，包含'+rows.at(-1).count+'本书',M,lastRow+54,{font:SANS,size:22,color:C.muted});
      if(rows.length<=3){
        const books=data.books.slice(0,4),spacing=(R-M)/books.length;
        const top=lastRow+(square?82:116);
        const imageTop=top+42;
        const wide=rows.length===1?(square?138:218):108;
        const height=H-121-imageTop;
        section('书架里的几本书',M,top-12,R-M,'02');
        for(const [i,book]of books.entries())await cover(book,M+i*spacing+(spacing-wide)/2,imageTop,wide,height,{shadow:true});
      }
      for(const row of rows)d.manifest.charts.push({kind:'category',encoding:'share-bar',...row,total:data.books.length});
    }
    async function timelinePage(d){
      const {H,M,R,text,block,line,dot,cover,section}=d,square=H===900;
      text('顺着这一年翻回去',M,175,{size:56,weight:600});
      text('有日期的阅读与笔记记录',M,226,{size:27,font:SANS,color:C.muted});
      if(!events.length){block('暂无带日期的阅读记录。',M,350,R-M,74,{size:34,min:32});await d.image(art.hero,190,464,520,H-578);return;}
      const buckets=new Map();for(const e of events){const k=e.date.slice(0,7);if(!buckets.has(k))buckets.set(k,[]);buckets.get(k).push(e);}
      const entries=[...buckets],limit=square?3:4,chosen=entries.length<=limit?entries:Array.from({length:limit},(_,i)=>entries[Math.round(i*(entries.length-1)/(limit-1))]);
      section('月份里的书页',M,289,R-M,'01');
      const top=354,bottom=H-169,rh=(bottom-top)/chosen.length;
      line(198,top+23,198,bottom-20,C.blue,1.5);
      for(const [i,[month,items]]of chosen.entries()){
        const y=top+i*rh,representative=items.find(e=>e.type==='读完')||items.find(e=>e.type==='开始阅读')||items[0];
        text(month.slice(5)+'月',M,y+45,{font:NUM,size:40,color:C.blue});dot(198,y+31,5,C.red);
        const ch=Math.min(119,rh-43);await cover(representative.book,231,y+12,84,ch,{shadow:false});
        block(representative.book.title,345,y+2,R-345,Math.min(102,rh-65),{size:32,min:28,weight:500,leading:1.35});
        const metaY=y+rh-24;
        text(`${representative.date.slice(5).replace('-','.')} · ${representative.type}`,345,metaY,{size:25,font:SANS,color:C.muted});
        text(`${items.length}条记录`,R,metaY,{size:25,font:SANS,color:C.blue,align:'right'});
        if(i<chosen.length-1)line(231,y+rh-9,R,y+rh-9);
      }
      text(`展示${chosen.length}个有记录的月份`,M,H-119,{size:25,font:SANS,color:C.muted});
      text(`共${events.length}条日期记录`,R,H-119,{size:25,font:SANS,color:C.blue,align:'right'});
      d.manifest.charts.push({kind:'timeline',total:events.length,months:buckets.size,shown:chosen.map(([month,items])=>({month,count:items.length}))});
    }
    async function bookPage(d,p){
      const {H,M,R,text,block,measureBlock,line,cover}=d,b=p.book,square=H===900,color=bookColor(b);
      const parts=b.title.match(/^(.{2,24}?)[：:]\s*(.+)$/);
      let title;
      if(parts){
        const main=block(parts[1],M,127,R-M,square?100:133,{size:58,min:36,weight:600,leading:1.2});
        title=block(parts[2],M,main.bottom+19,R-M,square?92:114,{size:38,min:30,weight:400,leading:1.35});
      }else{
        let size=56;
        // Avoid a lone final character in a headline; fit by the text, not by scaling the canvas.
        for(;size>36;size-=2){const fit=measureBlock(b.title,R-M,220,{size,min:size,weight:600,leading:1.2});if(!fit.cut&&(fit.rows.length<=1||fit.rows.at(-1).trim().length>=4))break;}
        title=block(b.title,M,127,R-M,220,{size,min:32,weight:600,leading:1.2});
      }
      const author=block(b.author,M,title.bottom+24,R-M,67,{size:27,min:25,font:SANS,color:C.muted,leading:1.35});
      const bodyY=author.bottom+32,mainBottom=H-260,available=mainBottom-bodyY;
      const primary=p.quote||'',kind=p.textKind==='thought'?'个人笔记':'原文摘录',rich=Boolean(primary),long=primary.length>(square?75:130);
      const bodyStyle={size:30,min:30,weight:400,font:SERIF,color:C.secondaryInk,leading:1.65,role:'book-body'};
      let excerpted=false;
      function excerpt(str,x,y,w,h,label){
        const fit=measureBlock(str,w,h,bodyStyle);excerpted=excerpted||fit.cut;
        text(label+(fit.cut?' · 节选':''),x,y-20,{size:24,weight:400,font:SANS,color,role:'book-label'});
        return block(str,x,y,w,h,bodyStyle);
      }
      if(available<140)throw Error('书名或作者过长，分享页内容超出安全版面，请缩短展示标题。');
      if(rich&&!long){
        const coverH=Math.min(330,available-90),qx=M+286,qw=R-qx;
        await cover(b,M+7,bodyY+8,222,coverH,{angle:-2,shadow:true});
        line(M+254,bodyY+5,M+254,mainBottom-9,color,1);
        const q=excerpt(primary,qx,bodyY+57,qw,available-63,kind);
        const secondary=[...b.thoughts.map(n=>({...n,label:'我的笔记'})),...b.highlights.map(n=>({...n,label:'另一处划线'}))],seen=new Set([primary]);
        let nextTop=q.bottom+55,added=0;
        for(const n of secondary){
          if(seen.has(n.text)||added===2)continue;seen.add(n.text);
          const height=mainBottom-nextTop-8;
          if(height<64||measureBlock(n.text,qw,height,bodyStyle).cut)continue;
          const item=excerpt(n.text,qx,nextTop,qw,height,n.label);nextTop=item.bottom+55;added++;
        }
        const categoryY=bodyY+coverH+38;
        if(b.category&&categoryY+51<mainBottom)block(b.category,M+7,categoryY,222,59,{size:28,min:26,color,leading:1.3});
      }else if(rich){
        const cw=112,ch=Math.min(157,available-22),qx=M,qw=R-M-171;
        await cover(b,R-cw-3,bodyY+6,cw,ch,{angle:2,shadow:true});
        excerpt(primary,qx,bodyY+58,qw,available-66,kind);
        const cy=bodyY+ch+38;
        if(b.category&&cy+84<mainBottom)block(b.category,R-135,cy,135,84,{size:28,min:25,color,leading:1.4});
      }else if(b.intro){
        const cw=244,ch=Math.min(377,available-24),tx=M+312;
        await cover(b,M+9,bodyY+9,cw,ch,{angle:-2,shadow:true});
        line(M+279,bodyY+5,M+279,mainBottom-9,color,1);
        excerpt(b.intro,tx,bodyY+57,R-tx,available-63,'内容简介');
      }else{
        const cw=296,tx=M+370,tw=R-tx;
        await cover(b,M+15,bodyY+7,cw,available-19,{angle:-2,shadow:true});
        line(M+335,bodyY+5,M+335,mainBottom-9,color,1);
        let next=bodyY;
        if(known(b.progress)){
          text('阅读状态',tx,next+27,{size:25,font:SANS,color:C.muted});
          const state=block(status(b),tx,next+48,tw,61,{size:40,min:32,weight:500,color});next=state.bottom+36;
        }
        if(b.category&&b.category!=='未分类'&&next+75<mainBottom){
          text('分类',tx,next+24,{size:25,font:SANS,color:C.muted});
          const cat=block(b.category,tx,next+44,tw,78,{size:32,min:28,color,leading:1.35});next=cat.bottom+32;
        }
        if(art.readingRecord&&mainBottom-next>=132)await d.image(art.readingRecord,tx,next,tw,mainBottom-next-4);
      }
      const metricY=H-200,mx=M+280,mw=R-mx;
      line(M,metricY-30,R,metricY-30,color,1);
      const hComplete=b.note_coverage?.highlights==='complete',tComplete=b.note_coverage?.thoughts==='complete';
      const cols=[[known(b.reading_seconds)?`${Math.floor(b.reading_seconds/3600)}小时\n${Math.floor(b.reading_seconds%3600/60)}分钟`:null,'阅读时长'],[hComplete&&(rich||b.highlights.length)?String(b.highlights.length):null,'条划线'],[tComplete&&(rich||b.thoughts.length)?String(b.thoughts.length):null,'条个人笔记']].filter(([v])=>v!==null);
      if(known(b.progress))d.progress(b,M,metricY+19,cols.length?230:R-M);
      else if(cols.length)block(status(b),M,metricY+3,230,54,{size:28,min:26,color:C.muted});
      if(cols.length)for(const [i,[v,label]]of cols.entries()){
        const x=mx+i*mw/cols.length,w=mw/cols.length-23,isTime=label==='阅读时长';
        if(i)line(x-15,metricY-1,x-15,metricY+84);
        block(v,x,isTime?metricY-11:metricY+6,w,isTime?75:60,{size:isTime?28:44,min:26,font:isTime?SANS:NUM,leading:1.35,color:i===0?color:C.ink});
        text(label,x,metricY+92,{font:SANS,size:24,color:C.muted});
      }
      d.manifest.material={highlights:b.highlights.length,thoughts:b.thoughts.length,kind:rich?kind:'book-info',long,excerpted};
    }
    return {render};
  }
  // Digest cards keep every line. Pagination happens before drawing and the
  // same page descriptor is used by preview, PNG and ZIP.
  function createDigest({analysis,source_mode='real'}){
    const fonts=()=>document.fonts.ready;
    const titleMode=analysis.input_mode==='title',footerHeight=132;
    // Detailed evidence and verification stay in the result's reference section.
    const exportLimits='';
    const height=ratio=>ratio==='1:1'?900:ratio==='4:5'?1125:1200;
    function wrap(ctx,str,width,size=32,font=SANS,weight=400){ctx.font=`${weight} ${size}px ${font}`;const rows=[];let line='';for(const ch of String(str).replace(/\r/g,'')){if(ch==='\n'){rows.push({text:line});line='';continue;}if(line&&ctx.measureText(line+ch).width>width){rows.push({text:line});line=ch;}else line+=ch;}if(line)rows.push({text:line});return rows;}
    async function pages(items,ratio){await fonts();const canvas=document.createElement('canvas'),ctx=canvas.getContext('2d');if(!ctx)throw Error('浏览器不支持 Canvas');const result=[],capacity=Math.floor((height(ratio)-270-(footerHeight-84))/48);for(const item of items){const limits=item.kind==='review'?'':exportLimits;const content=[...wrap(ctx,analysis.book?.title||'电子书精华',764,38,SERIF,600).map(r=>({...r,size:38,weight:600})),...wrap(ctx,analysis.book?.author||'',764).map(r=>({...r,size:32,weight:400})),{text:'',size:32},...wrap(ctx,item.title,764,38,SERIF,600).map(r=>({...r,size:38,weight:600})),{text:'',size:32},...wrap(ctx,item.text+limits,764).map(r=>({...r,size:32,weight:400}))];for(let start=0;start<content.length;start+=capacity)result.push({id:item.id+'-'+Math.floor(start/capacity),title:item.title,kind:item.kind,part:Math.floor(start/capacity)+1,parts:Math.ceil(content.length/capacity),rows:content.slice(start,start+capacity)});}return result;}
    async function render(page,ratio){await fonts();const canvas=document.createElement('canvas');canvas.width=900;canvas.height=height(ratio);const ctx=canvas.getContext('2d'),W=900,H=canvas.height,M=64;const manifest={version:'digest-1',page:page.id,width:W,height:H,footerTop:H-footerHeight,text:[],blocks:[],charts:[],images:[],spacing:[]};canvas.readingLayout=manifest;
      const text=(str,x,y,size=28,font=SANS,color=C.ink,weight=400,role='content')=>{ctx.font=`${weight} ${size}px ${font}`;ctx.fillStyle=color;ctx.textBaseline='alphabetic';ctx.fillText(str,x,y);const m=ctx.measureText(str);if(str.trim())manifest.text.push({text:str,x:x-m.actualBoundingBoxLeft,y:y-m.actualBoundingBoxAscent,w:m.actualBoundingBoxLeft+m.actualBoundingBoxRight,h:m.actualBoundingBoxAscent+m.actualBoundingBoxDescent,size,role});};
      const rule=y=>{ctx.strokeStyle=C.line;ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(M,y);ctx.lineTo(W-M,y);ctx.stroke();};
      ctx.fillStyle=C.paper;ctx.fillRect(0,0,W,H);ctx.strokeStyle=C.line;ctx.strokeRect(22,22,W-44,H-44);text('年年阅',M,72,28,SERIF,C.ink,600);text('书中精华',530,72,24,SANS,C.muted);rule(95);
      page.rows.forEach((row,i)=>text(row.text,M,160+i*48,row.size||32,(row.weight||400)===600?SERIF:SANS,C.ink,row.weight||400));manifest.blocks.push({x:M,y:122,w:772,h:H-238-(footerHeight-84),cut:false});rule(H-footerHeight);{text((source_mode==='sample'?'功能测试示例 · ':'')+(titleMode?'基于公开资料，未核验全文':('基于所提供正文'+(analysis.quality_status==='needs_review'?' · 方法待核查':''))),M,H-96,23,SANS,C.muted,400,'footer');text((analysis.reading_status?.level==='partial'?'部分解读 · ':'')+'出处与资料范围见结果页',M,H-64,23,SANS,C.muted,400,'footer');}text(`${page.part} / ${page.parts}`,M,H-32,24,NUM,C.muted,400,'footer');return canvas;
    }
    return {pages,render};
  }
  return {create,createDigest};
})();
