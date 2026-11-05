"""Evidence-linked, non-psychometric reading-style indices. No keyword typing."""
import html
from datetime import date,timedelta
from collections import Counter,defaultdict

PAIRS=(('EI','外倾','内倾'),('SN','实感','直觉'),('TF','思考','情感'),('JP','判断','感知'))

def profile(signals,books,year):
    if not isinstance(signals,list):raise ValueError('阅读倾向标注须为列表')
    thoughts={}
    for b in books:
        for t in b.get('thoughts',[]):
            when=t.get('created_at') or ''
            try: valid_date=date.fromisoformat(when[:10]).year==year
            except (ValueError,TypeError):valid_date=False
            if valid_date and t.get('source_id'):
                thoughts[t['source_id']]={**t,'book_id':b['book_id'],'book_title':b.get('title',''),'month':when[:7]}
    valid=[];seen=set()
    for s in signals:
        if not isinstance(s,dict):raise ValueError('无效阅读倾向标注')
        axis=s.get('axis');sid=s.get('source_id');side=s.get('side')
        if axis not in ('EI','SN','TF','JP') or not isinstance(side,str) or len(side)!=1 or side not in axis or not isinstance(sid,str) or sid not in thoughts or not isinstance(s.get('reason'),str) or not 1<=len(s['reason'])<=300:
            raise ValueError('倾向须对应本年个人想法及有效维度，不可用划线冒充')
        if (axis,sid) in seen:raise ValueError('重复倾向依据')
        seen.add((axis,sid));valid.append({**s,**thoughts[sid]})
    def aggregate(rows):
        axes=[];letters=[]
        for pair,left,right in PAIRS:
            evidence=[s for s in rows if s['axis']==pair]
            perbook=defaultdict(list)
            for s in evidence:perbook[s['book_id']].append(s)
            percent=None
            if len(evidence)>=3 and len(perbook)>=2:
                percent=round(100*sum(sum(s['side']==pair[0] for s in group)/len(group) for group in perbook.values())/len(perbook))
            letter='?' if percent is None or 45<=percent<=55 else pair[0] if percent>55 else pair[1]
            letters.append(letter)
            axes.append({'pair':pair,'left_label':left,'right_label':right,'left_percent':percent,
                         'right_percent':None if percent is None else 100-percent,'letter':letter,
                         'evidence':[{'book':s['book_title'],'text':s['text'],'reason':s['reason']} for s in evidence]})
        return {'type':''.join(letters) if '?' not in letters else '倾向未明','axes':axes}
    return {'annual':aggregate(valid),'months':{f'{year}-{m:02}':aggregate([s for s in valid if s['month']==f'{year}-{m:02}']) for m in range(1,13)}}

def section(data):
    p=profile(data.get('reading_signals',[]),data['books'],data['year'])
    esc=lambda x:html.escape(str(x))
    def panel(value):
        out='<strong class="portrait-type">'+esc(value['type'])+'</strong><div class="portrait-axes">'
        for a in value['axes']:
            n=a['left_percent']; pair=a['pair']
            out+='<div class="portrait-axis"><div><b>'+pair[0]+' '+a['left_label']+(' · '+str(n)+'%' if n is not None else '')+'</b><span>'+pair[1]+' '+a['right_label']+(' · '+str(100-n)+'%' if n is not None else '')+'</span></div>'
            out+=('<meter min="0" max="100" value="'+str(n)+'" aria-label="'+esc(pair+' 左侧倾向 '+str(n)+'%')+'"></meter>') if n is not None else '<p class="muted">本期有效依据不足，暂不填写比例</p>'
            if a['evidence']:
                out+='<details><summary>为什么这样判断</summary>'
                for e in a['evidence']:out+='<p>'+esc(e['reason'])+'</p><blockquote>'+esc(e['text'])+'</blockquote><small>'+esc(e['book'])+'</small>'
                out+='</details>'
            out+='</div>'
        return out+'</div>'
    result='<section class="chapter reading-portrait" id="readingPortrait"><div class="chapter-heading"><h2>书架里的另一个我</h2></div><p class="muted">阅读 MBTI · 趣味推测。比例描述材料中的阅读风格，不是人格概率或正式测评分数。</p><label>查看月份 <select id="portraitMonth"><option value="annual">全年阅读侧写</option>'
    for month in p['months']:
        if month<=str(data.get('as_of') or f"{data['year']}-12-31")[:7]:result+='<option value="'+month+'">'+month+'</option>'
    result+='</select></label><div data-portrait-period="annual">'+panel(p['annual'])+'</div>'
    for month,value in p['months'].items():result+='<div data-portrait-period="'+month+'" hidden>'+panel(value)+'</div>'
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
        palette=['#b83225','#205ac5','#e0a521','#167c70','#a65a96','#dc793e','#eadcc5']
        result+='<article class="insight-chart"><h3>时间花在哪里</h3><svg viewBox="0 0 120 120" width="160" role="img" aria-label="分类时长占比环形图">'
        offset=0
        for i,(name,value) in enumerate(values):
            length=value/total*251.327
            result+='<circle cx="60" cy="60" r="40" fill="none" stroke="'+palette[i%len(palette)]+'" stroke-width="16" stroke-dasharray="'+str(length)+' '+str(251.327-length)+'" stroke-dashoffset="'+str(-offset)+'" transform="rotate(-90 60 60)"><title>'+esc(name)+' '+str(round(value/total*100))+'%</title></circle>'
            offset+=length
        result+='</svg><p class="muted">'+esc(' · '.join(name+' '+str(round(v/total*100))+'%' for name,v in values))+'</p></article>'
    read,listen=features.get('read_seconds'),features.get('listen_seconds')
    if read is not None and listen is not None:result+=bars('看书与听书 · 小时',[('文字阅读',round(read/3600,1)),('听书',round(listen/3600,1))])
    return result+'</div></section><script id="portrait-controller">document.getElementById("portraitMonth").addEventListener("change",e=>document.querySelectorAll("[data-portrait-period]").forEach(p=>p.hidden=p.dataset.portraitPeriod!==e.target.value));</script>'
