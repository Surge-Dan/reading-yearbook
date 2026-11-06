"""Evidence-linked, non-psychometric reading-style indices. No keyword typing."""
import html
from datetime import date,timedelta
from collections import Counter,defaultdict

PAIRS=(('EI','外倾','内倾'),('SN','实感','直觉'),('TF','思考','情感'),('JP','判断','感知'))

def profile(signals,books,year):
    if not isinstance(signals,list):raise ValueError('阅读倾向标注须为列表')
    records={}
    for b in books:
        for kind,field in (('thought','thoughts'),('highlight','highlights')):
            for t in b.get(field,[]):
                when=t.get('created_at') or ''
                try: valid_date=date.fromisoformat(when[:10]).year==year
                except (ValueError,TypeError):valid_date=False
                if valid_date and t.get('source_id'):
                    records[kind,t['source_id']]={**t,'book_id':b['book_id'],'book_title':b.get('title',''),'month':when[:7]}
    valid=[];seen=set()
    for s in signals:
        if not isinstance(s,dict):raise ValueError('无效阅读倾向标注')
        axis=s.get('axis');sid=s.get('source_id');side=s.get('side')
        kind=s.get('source_kind','thought')
        if axis not in ('EI','SN','TF','JP') or not isinstance(side,str) or len(side)!=1 or side not in axis or kind not in ('thought','highlight') or not isinstance(sid,str) or (kind,sid) not in records or not isinstance(s.get('reason'),str) or not 1<=len(s['reason'])<=300:
            raise ValueError('倾向须对应本年有效的个人想法或划线')
        if (axis,kind,sid) in seen:raise ValueError('重复倾向依据')
        seen.add((axis,kind,sid))
        valid.append({**records[kind,sid],'axis':axis,'side':side,'reason':s['reason'],'source_kind':kind})
    def aggregate(rows):
        axes=[];letters=[]
        for pair,left,right in PAIRS:
            evidence=[s for s in rows if s['axis']==pair]
            perbook=defaultdict(list)
            for s in evidence:perbook[s['book_id']].append(s)
            percent=None
            if len(evidence)>=3 and len(perbook)>=2 and any(s['source_kind']=='thought' for s in evidence):
                left_votes=weight_total=0
                for group in perbook.values():
                    thoughts=[s for s in group if s['source_kind']=='thought']
                    active=thoughts or group
                    weight=2 if thoughts else 1
                    left_votes+=weight*sum(s['side']==pair[0] for s in active)/len(active)
                    weight_total+=weight
                percent=round(100*left_votes/weight_total)
            letter='?' if percent is None or 45<=percent<=55 else pair[0] if percent>55 else pair[1]
            letters.append(letter)
            axes.append({'pair':pair,'left_label':left,'right_label':right,'left_percent':percent,
                         'right_percent':None if percent is None else 100-percent,'letter':letter,
                         'evidence':[{'book':s['book_title'],'text':s['text'],'reason':s['reason'],'source_kind':s['source_kind']} for s in evidence]})
        return {'type':''.join(letters) if '?' not in letters else '倾向未明','axes':axes}
    return {'annual':aggregate(valid),'months':{f'{year}-{m:02}':aggregate([s for s in valid if s['month']==f'{year}-{m:02}']) for m in range(1,13)}}

def section(data):
    p=profile(data.get('reading_signals',[]),data['books'],data['year'])
    esc=lambda x:html.escape(str(x))
    def panel(value):
        out=''
        if value['type']!='倾向未明':
            out='<strong class="portrait-type">'+esc(value['type'])+'</strong>'
        out+='<div class="portrait-axes">'
        for a in value['axes']:
            n=a['left_percent']; pair=a['pair']
            out+='<div class="portrait-axis"><div><b>'+pair[0]+' '+a['left_label']+(' · '+str(n)+'%' if n is not None else '')+'</b><span>'+pair[1]+' '+a['right_label']+(' · '+str(100-n)+'%' if n is not None else '')+'</span></div>'
            out+=('<meter min="0" max="100" value="'+str(n)+'" aria-label="'+esc(pair+' 左侧倾向 '+str(n)+'%')+'"></meter>') if n is not None else '<p class="muted">现有记录不足以估计比例</p>'
            if a['evidence']:
                out+='<details><summary>为什么这样判断</summary>'
                for e in a['evidence']:
                    label='个人想法' if e['source_kind']=='thought' else '划线'
                    out+='<p>'+esc(e['reason'])+'</p><blockquote>'+esc(e['text'])+'</blockquote><small>'+label+' · '+esc(e['book'])+'</small>'
                out+='</details>'
            out+='</div>'
        return out+'</div>'
    result='<section class="chapter reading-portrait" id="readingPortrait"><div class="chapter-heading"><h2>书架里的另一个我</h2></div><p class="muted portrait-scope">全年阅读侧写 · 根据个人想法和划线估计阅读倾向</p>'
    result+=panel(p['annual'])
    result+='</section><section class="chapter"><div class="chapter-heading"><h2>阅读里的小发现</h2></div><div class="insight-grid">'
    def bars(title,items):
        peak=max((v for _,v in items),default=1) or 1
        return '<article class="insight-chart"><h3>'+title+'</h3>'+''.join('<div class="insight-bar"><span>'+esc(k)+'</span><meter min="0" max="'+str(peak)+'" value="'+str(v)+'" aria-label="'+esc(k)+'"></meter><b>'+esc(v)+'</b></div>' for k,v in items)+'</article>'
    counts=Counter(b['category'] for b in data['books'])
    result+=bars('书架的主题分布 · 本数',counts.most_common())
    notes=Counter((t.get('created_at') or '')[:7] for b in data['books'] for t in b.get('highlights',[])+b.get('thoughts',[]) if (t.get('created_at') or '').startswith(str(data['year'])))
    result+=bars('每月留下的记录 · 条数',sorted(notes.items()))
    progress=Counter('未记录' if b.get('progress') is None else '100%' if b['progress']>=100 else '75–99%' if b['progress']>=75 else '50–74%' if b['progress']>=50 else '25–49%' if b['progress']>=25 else '0–24%' for b in data['books'])
    result+=bars('当前进度 · 不是年度读完数',sorted(progress.items()))
    rows=[(b['title'],round(b['reading_seconds']/3600,1)) for b in data['books'] if b.get('reading_seconds') is not None]
    result+=bars('已知逐书投入 · 小时',sorted(rows,key=lambda x:-x[1])[:10])
    features=data.get('features') or {}
    hourly=features.get('hourly') or []
    if len(hourly)==24:result+=bars('阅读时钟 · 小时',[(str(i)+'时',round(n/3600,1)) for i,n in enumerate(hourly) if n is not None])
    daily=features.get('daily') or {}
    if daily:
        result+='<article class="insight-chart"><h3>阅读日历 · 已取得日期</h3><div class="reading-calendar">'
        peak=max(daily.values()) or 1
        day=date(data['year'],1,1)
        try:end=min(date.fromisoformat(data['as_of']),date(data['year'],12,31))
        except (ValueError,TypeError,KeyError):end=date(data['year'],12,31)
        result+=''.join('<span class="unknown" aria-hidden="true"></span>' for _ in range(day.weekday()))
        while day<=end:
            key=day.isoformat();n=daily.get(key)
            result+=('<span class="unknown" title="'+key+' · 未取得"></span>') if n is None else '<span style="opacity:'+str(.2+.8*n/peak)+'" title="'+key+' · '+str(round(n/60))+'分钟"></span>'
            day+=timedelta(days=1)
        result+='</div><p class="muted">未取得的日期不补零。</p></article>'
        bins=Counter('0–15分钟' if n<900 else '15–30分钟' if n<1800 else '30–60分钟' if n<3600 else '60分钟以上' for n in daily.values() if n>0)
        result+=bars('阅读日时长分布',[(k,bins[k]) for k in ('0–15分钟','15–30分钟','30–60分钟','60分钟以上')])
    categories=[r for r in features.get('category_time',[]) if r.get('seconds') is not None and r['seconds']>0]
    if categories:
        result+=bars('分类投入 · 小时',[(r['name'],round(r['seconds']/3600,1)) for r in categories])
        values=[(r['name'],r['seconds']) for r in categories]
        total=max(sum(v for _,v in values),data['summary'].get('seconds') or 0)
        if total>sum(v for _,v in values):values.append(('未归属',total-sum(v for _,v in values)))
        values.sort(key=lambda row:-row[1])
        palette=['#b83225','#205ac5','#e0a521','#167c70','#a65a96','#dc793e']
        hours,minutes=divmod(round(total/60),60)
        duration=f'{hours}小时{minutes}分' if hours else f'{minutes}分钟'
        result+='<article class="insight-chart"><h3>时间花在哪里</h3><div class="insight-ring-layout"><div class="insight-ring"><svg viewBox="10 10 100 100" aria-hidden="true">'
        legend=[]
        offset=0
        for i,(name,value) in enumerate(values):
            length=value/total*251.327
            color='#eadcc5' if name=='未归属' else palette[i%len(palette)]
            share=f'{value/total:.0%}'
            result+='<circle cx="60" cy="60" r="40" fill="none" stroke="'+color+'" stroke-width="16" stroke-dasharray="'+str(length)+' '+str(251.327-length)+'" stroke-dashoffset="'+str(-offset)+'" transform="rotate(-90 60 60)"/>'
            legend.append('<li><span class="insight-ring-swatch" style="background:'+color+'"></span><span>'+esc(name)+'</span><b>'+share+'</b></li>')
            offset+=length
        result+='</svg><div class="insight-ring-total"><b>'+duration+'</b><small>总时长</small></div></div><ul class="insight-ring-legend" aria-label="分类时长占比">'+''.join(legend)+'</ul></div></article>'
    read,listen=features.get('read_seconds'),features.get('listen_seconds')
    if read is not None and listen is not None:result+=bars('看书与听书 · 小时',[('文字阅读',round(read/3600,1)),('听书',round(listen/3600,1))])
    return result+'</div></section>'
