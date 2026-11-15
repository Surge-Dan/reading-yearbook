/* One workbench for hosted uploads and portable, offline results. */
(() => {
  'use strict';
  const mount=()=>{
    const root=document.getElementById('ebook');if(!root||root.dataset.mounted)return;root.dataset.mounted='true';
    const $=id=>root.querySelector('#'+id),readonly=root.dataset.readerMode==='readonly',config=readonly?{}:window.EBOOK_CONFIG||{},online=!readonly&&typeof config.token==='string'&&config.token.length>0;
    const embedded=JSON.parse(document.getElementById('reading-data')?.textContent||'{}'),bundles=embedded.distillations||[];
    let result=bundles[0]||window.EBOOK_RESULT||null,job=null,runnerAvailable=false,agentMode=false,poll=null,requestGeneration=0,requestBusy=false,shareItems=[],sharePages=[],shareArt=null,renderSequence=0;
    if(readonly&&!result){root.hidden=true;document.querySelectorAll('a[href="#ebook"]').forEach(a=>a.hidden=true);return;}
    const activeStates=['queued','running','awaiting_agent','awaiting_response','needs_book_confirmation'];
    const el=(tag,text,cls)=>{const node=document.createElement(tag);if(text!=null)node.textContent=String(text);if(cls)node.className=cls;return node;};
    const describe=value=>typeof value==='string'?value:value==null?'':JSON.stringify(value,null,2);
    const safeName=()=>((result?.analysis?.book?.title||'电子书精华').replace(/[<>:"/\\|?*\x00-\x1f]/g,'-').slice(0,80)||'电子书精华');
    const notice=text=>{$('ebookActionStatus').textContent=text;};
    const sourceTypes={author:'作者公开资料',publisher:'出版社资料',preview:'公开试读',interview:'作者访谈',secondary:'二手资料'};
    const scope=()=>(result?.analysis?.input_mode==='title'?'基于公开资料，未核验全文':'基于所提供正文')+(result?.source_mode==='sample'?' · 功能测试示例':'');
    const sourceLabel=(item,source)=>item.source_verified===false||source.source_verified===false?(result?.analysis?.input_mode==='title'?'模型返回引文 · 未通过资料核对':'模型返回引文 · 未通过原文核对'):source.source_type?sourceTypes[source.source_type]||'公开资料':'原文';
    function sourceLink(parent,url,label){try{const u=new URL(url);if(!['https:','http:'].includes(u.protocol)||u.username||u.password)return;const link=el('a',label,'ebook-source-link');link.href=u.href;link.target='_blank';link.rel='noopener noreferrer';parent.append(link);}catch{}}
    function sources(parent,item){for(const s of item.sources||[]){const b=el('blockquote');b.append(el('span',sourceLabel(item,s)+' · '+(s.location||s.element_id||'位置未记录'),'ebook-source-label'),el('p',s.quote||''));if(s.url)sourceLink(b,s.url,'查看实际资料');parent.append(b);}}
    const readerText=value=>String(value).replace(/^AI\s*(?:解释|整理)\s*[：:]\s*/, '');
    function textParts(item,kind){const out=[];if(kind==='overview')return describe(item);if(item.case_origin==='ai_exercise')out.push('应用示例（不是原书案例）');for(const k of ['explanation','interpretation','text','why_it_matters'])if(item[k])out.push(readerText(item[k]));if(item.trigger)out.push('什么时候用：'+item.trigger);if(item.steps?.length)out.push('怎么做：\n'+item.steps.map((s,i)=>`${i+1}. ${s}`).join('\n'));if(item.example)out.push('案例／示例：'+item.example);if(item.boundaries?.length)out.push('使用提醒：\n'+item.boundaries.join('\n'));for(const k of ['summary','definition'])if(item[k])out.push(readerText(item[k]));return out.join('\n\n');}
    function digestText(){
      if(!result?.analysis)return '';
      const a=result.analysis,parts=['# '+(a.book?.title||'书籍精华'),describe(a.overview)];
      for(const [key,title]of [['book_context','读懂这本书'],['themes','核心观点'],['methods','值得带走的方法'],['cases','关键案例'],['counterexamples','反例'],['insights','读完想带走的东西']])if(a[key]?.length)parts.push('## '+title,...a[key].map(item=>'### '+(item.title||'')+'\n\n'+textParts(item,key)));
      for(const item of a.reading_lenses||[])parts.push('## '+item.title,item.text);
      for(const item of a.memorable_passages||[])parts.push('## 值得保留的金句','> '+item.text.replace(/\n/g,'\n> '),item.why_it_matters);
      if(a.review?.status==='ready')parts.push('## 读后余味',...a.review.paragraphs.map(p=>p.text));
      return parts.filter(Boolean).join('\n\n');
    }
    function copyButton(parent,text){const b=el('button','复制这条','text-button');b.type='button';b.dataset.ebookCopy='true';b.onclick=()=>copy(text);parent.append(b);}
    function resultSection(title){const s=el('section');s.append(el('h3',title));$('ebookResult').append(s);return s;}
    let readingObserver,updateReading=()=>{};
    const masthead=document.querySelector('.masthead');
    const resizeReading=()=>root.style.setProperty('--distill-nav-top',((masthead?.getBoundingClientRect().height||0)+1)+'px');
    resizeReading();if(masthead)new ResizeObserver(resizeReading).observe(masthead);
    window.addEventListener('scroll',()=>updateReading(),{passive:true});
    function renderResult(){
      if(!result?.analysis)return;
      const a=result.analysis,light=a.pipeline_version?.startsWith('reading-light-'),container=$('ebookResult');window.EBOOK_RESULT=result;
      readingObserver?.disconnect();$('ebookResultShell').hidden=false;container.replaceChildren();shareItems=[];
      $('ebookBookTitle').textContent=a.book?.title||'电子书精华';$('ebookAuthor').textContent=(a.book?.author||'')+(a.book?.edition?' · '+a.book.edition:'');
      $('ebookQuality').textContent='';$('ebookQuality').hidden=true;
      const nav=el('div',null,'ebook-reading-nav');const links=el('nav');links.setAttribute('aria-label','阅读章节');nav.append(links);container.append(nav);
      const sections=[];
      function section(title,key){const node=resultSection(title);node.id='ebook-reading-'+key;node.dataset.readingSection=key;const link=el('a',title);link.href='#'+node.id;links.append(link);sections.push({node,link});return node;}
      function details(parent,label){const d=el('details');d.append(el('summary',label));parent.append(d);return d;}
      function prose(value){if(typeof value==='string')return value;if(!value||typeof value!=='object')return '';return Object.values(value).filter(v=>typeof v==='string').join('\n\n');}
      function addItem(parent,item,key,index){
        const article=el('article'),heading=item.title||item.term||'';if(heading)article.append(el('h4',heading));
        for(const [label,k]of [['','explanation'],['','interpretation'],['什么时候用：','trigger'],['案例／示例：','example'],['','summary'],['','definition']])if(item[k])article.append(el('p',label+readerText(prose(item[k]))));
        for(const [label,k,tag]of [['怎么做','steps','ol'],['使用提醒','boundaries','ul']])if(item[k]?.length){article.append(el('p',label,'ebook-method-label'));const list=el(tag);item[k].forEach(t=>list.append(el('li',prose(t))));article.append(list);}
        if(item.case_origin==='ai_exercise')article.append(el('p','应用示例（不是原书案例）','ebook-meta'));
        const body=textParts(item,key);copyButton(article,heading+'\n\n'+body);parent.append(article);shareItems.push({id:key+'-'+(item.id||index),kind:key,title:heading||parent.querySelector('h3')?.textContent||key,text:body});
      }
      const overviewText=prose(a.overview);if(overviewText){const title=light?'这本书讲什么':'书籍概览',overview=section(title,'overview');overviewText.split(/\n\s*\n/).filter(Boolean).forEach(p=>overview.append(el('p',p)));copyButton(overview,overviewText);shareItems.push({id:'overview',kind:'overview',title,text:overviewText});}
      if(a.book_context?.length){const s=section('读懂这本书','book-context');a.book_context.forEach((item,i)=>addItem(s,item,'book_context',i));}
      for(const [key,title]of [['themes',light?'最值得记住的东西':'核心观点'],['methods','值得带走的方法'],['cases','关键案例'],['counterexamples','反例'],['insights',light?'读完想带走的东西':'对我的启发']])if(a[key]?.length){const s=section(title,key);a[key].forEach((item,i)=>addItem(s,item,key,i));}
      for(const [i,item]of (a.reading_lenses||[]).entries()){const s=section(item.title,'lens-'+i);s.append(el('p',item.text));copyButton(s,item.title+'\n\n'+item.text);shareItems.push({id:'lens-'+i,kind:'reading_lenses',title:item.title,text:item.text});}
      if(a.memorable_passages?.length){const s=section('值得保留的金句','passages');a.memorable_passages.forEach((item,i)=>{const article=el('article'),body='原文：\n'+item.text+'\n\n为什么记住它：\n'+item.why_it_matters;article.append(el('blockquote',item.text),el('p',item.why_it_matters));copyButton(article,body);s.append(article);shareItems.push({id:'passage-'+i,kind:'memorable_passages',title:'值得保留的金句',text:body});});}
      const review=a.review;
      if(review?.status==='ready'&&review.paragraphs?.some(p=>p.text)){
        const reviewTitle=light?'读后余味':'我的书评',s=section(reviewTitle,'review');
        review.paragraphs.forEach((paragraph,i)=>{if(!paragraph.text)return;const article=el('article',null,'ebook-review-paragraph');article.append(el('p',paragraph.text));
          const body=paragraph.text,shareText=paragraph.text;
          copyButton(article,body);s.append(article);shareItems.push({id:'review-'+i,kind:'review',title:reviewTitle+' · '+(i+1),text:shareText});});
      }
      const themes=container.querySelector('[data-reading-section="themes"]');
      if(themes){const grid=el('div',null,'distill-theme-grid');themes.querySelectorAll(':scope>article').forEach(a=>grid.append(a));themes.append(grid);}
      updateReading=()=>{
        const edge=(masthead?.getBoundingClientRect().height||0)+155;
        let current=sections.filter(({node})=>node.getBoundingClientRect().top<=edge).at(-1)||sections[0];
        if(innerHeight+scrollY>=document.documentElement.scrollHeight-4)current=sections.at(-1);
        for(const entry of sections){if(entry===current){entry.link.setAttribute('aria-current','location');entry.link.dataset.active='true';}else{entry.link.removeAttribute('aria-current');delete entry.link.dataset.active;}}
      };updateReading();
    }
    async function api(path,options={}){const response=await fetch((config.apiBase||'')+path,{...options,credentials:'same-origin',headers:{'X-Ebook-Token':config.token,...options.headers}});let payload;try{payload=await response.json();}catch{throw Error('工作台返回了无法读取的响应');}if(!response.ok)throw Error(payload.error||payload.message||`请求失败 (${response.status})`);return payload;}
    function invalidateRequests(){clearTimeout(poll);return ++requestGeneration;}
    function titleEnabled(){if($('ebookTitleSubmit'))$('ebookTitleSubmit').disabled=!online||!runnerAvailable||!agentMode||requestBusy||Boolean(job&&(activeStates.includes(job.state)||job.state==='needs_approval'));}
    function lost(error){runnerAvailable=false;$('ebookFile').disabled=true;titleEnabled();$('ebookConnection').textContent='工作台连接已断开：'+error.message+'。请让助手重新打开工作台，或点击刷新状态。';if(job&&activeStates.includes(job.state))$('ebookStatus').textContent='连接已断开，暂无法确认任务进度。刷新状态后可恢复。';clearTimeout(poll);}
function showJob(current){job=current;$('ebookTask').hidden=false;$('ebookFilename').textContent=current.filename||'';const states={queued:'准备处理',running:'正在处理',awaiting_agent:'等待当前助手开始',awaiting_response:'等待当前助手提交分析',needs_approval:'等待范围确认',completed:'精华已生成',failed:'处理失败',cancelled:'已取消',interrupted:'处理已中断'},stage=current.stage||'',stageName=stage.startsWith('reading-review')?'撰写书评':stage.startsWith('title-research')?'查阅公开资料':stage.startsWith('title-analysis')?'整理书籍解读':stage.startsWith('title-review')?'撰写书评':stage.startsWith('stage0')?'理解全书':stage.startsWith('extract')?'提炼观点与方法':stage.startsWith('verif')?'核验来源与任务':stage.startsWith('ria')?'整理方法':stage.startsWith('organization')?'整理全书结构':stage.startsWith('analysis')?'生成精华':stage.startsWith('pressure')?'任务演练':stage==='complete'?'生成结果':stage==='budget'?'等待范围确认':stage.startsWith('parse')?'解析正文':states[current.state]||'正在处理';$('ebookStatus').textContent=(current.message||states[current.state]||current.state)+(current.error?' · '+current.error:'');$('ebookProgress').textContent=Number.isFinite(current.total)&&current.total>0?`当前阶段：${stageName} · 已完成 ${current.completed??0} / ${current.total} 项处理`:`当前阶段：${stageName}`;
      $('ebookStartInstruction').hidden=!agentMode||current.state!=='awaiting_agent';$('ebookCancel').hidden=!activeStates.includes(current.state);$('ebookRetry').hidden=!['failed','cancelled','interrupted'].includes(current.state);$('ebookApprove').hidden=current.state!=='needs_approval';$('ebookBudget').hidden=current.state!=='needs_approval';$('ebookBudget').textContent=current.estimate?'本次处理范围超出普通单书规模：'+(agentMode?`正文 ${current.estimate.characters??'未知'} 字符，预计至少 ${current.estimate.minimum_model_calls??'未知'} 个分析阶段；仍会消耗当前助手额度。`:describe(current.estimate))+'。确认后将继续当前书籍。':'';
      const active=activeStates.includes(current.state)||current.state==='needs_approval';$('ebookUpload').disabled=active;$('ebookFile').disabled=active||!runnerAvailable;titleEnabled();if($('ebookBookChoice')){$('ebookBookChoice').hidden=current.state!=='needs_book_confirmation';$('ebookBookCandidates').replaceChildren();if(current.state==='needs_book_confirmation')for(const candidate of current.book_candidates||[]){const button=el('button',candidate.title+' · '+candidate.author+' · '+candidate.edition,'button ebook-book-candidate');button.type='button';button.onclick=()=>chooseBook(current.id,candidate.id,current.selection_id);$('ebookBookCandidates').append(button);}}clearTimeout(poll);if(current.state==='completed'&&current.analysis){result={analysis:current.analysis,digest:current.digest||'',result_url:current.result_url};renderResult();}if(activeStates.includes(current.state))poll=setTimeout(refreshJob,1000);}
    async function refreshJob(){if(!job)return;const id=job.id,generation=requestGeneration;try{const response=await api('/api/jobs/'+encodeURIComponent(id));if(generation===requestGeneration&&job?.id===id&&response.job?.id===id)showJob(response.job);}catch(e){if(generation===requestGeneration&&job?.id===id)lost(e);}}
    async function connect(){if(requestBusy)return;const generation=invalidateRequests();if(!online){$('ebookFile').disabled=true;$('ebookConnection').textContent='当前为离线结果页。要创建新任务，请让助手重新打开年年阅工作台。';$('ebookReconnect').hidden=true;return;}try{const state=await api('/api/state');if(generation!==requestGeneration)return;runnerAvailable=Boolean(state.runner?.available);agentMode=state.runner?.mode==='current-agent-instructed-tools';$('ebookFile').disabled=!runnerAvailable;$('ebookConnection').textContent=agentMode?'当前助手分析：提交书名或上传后，回到同一对话说“开始蒸馏”。无需另外连接 Codex / Claude Code。':runnerAvailable?'已检测到 '+(state.runner.name||'AI')+' 自动执行入口；仅支持上传模式。书名模式请让助手以 agent 模式重开工作台。':'未检测到可用的 AI 执行入口。请让助手检查本机配置后重新打开工作台。';if(!agentMode)$('ebookUploadNote').textContent='选择文件后直接开始。正文将在本机解析，并发送到所选自动执行入口的模型服务。扫描 PDF 暂不支持。';const latest=(state.jobs||[])[0];if(latest)showJob(latest);}catch(e){if(generation===requestGeneration)lost(e);}finally{titleEnabled();}}
    for(const mode of ['Title','Upload'])if($('ebook'+mode+'Tab'))$('ebook'+mode+'Tab').onclick=()=>{for(const other of ['Title','Upload']){$('ebook'+other+'Tab').setAttribute('aria-pressed',String(other===mode));$('ebook'+other+'Panel').hidden=other!==mode;}};
    if($('ebookTitleSubmit'))$('ebookTitleSubmit').onclick=async()=>{if(requestBusy||!online||!runnerAvailable||!agentMode)return;const title=$('ebookTitleInput').value.trim();if(!title){$('ebookConnection').textContent='请先填写书名。';$('ebookTitleInput').focus();return;}const generation=invalidateRequests();requestBusy=true;titleEnabled();try{const response=await api('/api/title-jobs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({title,author:$('ebookAuthorInput').value.trim(),focus:$('ebookFocus').value.trim()})});if(generation===requestGeneration){showJob(response.job);notice('书名已接收，请回同一对话说“开始蒸馏”。');}}catch(e){if(generation===requestGeneration){$('ebookConnection').textContent='提交失败：'+e.message;if(job)showJob(job);}}finally{requestBusy=false;titleEnabled();}};
    async function chooseBook(id,bookId,selectionId){if(requestBusy||job?.id!==id)return;const generation=invalidateRequests();requestBusy=true;try{const response=await api('/api/jobs/'+id+'/select-book',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({book_id:bookId,selection_id:selectionId})});if(generation===requestGeneration&&job?.id===id)showJob(response.job);}catch(e){if(generation===requestGeneration&&job?.id===id){notice('选择失败：'+e.message);showJob(job);}}finally{requestBusy=false;titleEnabled();}}
    if($('ebookUpload'))$('ebookUpload').onclick=()=>{if(!online||!runnerAvailable){$('ebookConnection').textContent='请让助手重新打开年年阅工作台，并检查 AI 执行入口。';return;}$('ebookFile').click();};
    if($('ebookFile'))$('ebookFile').onchange=async()=>{const file=$('ebookFile').files[0];if(!file||requestBusy)return;if(!/\.(epub|pdf|txt|md)$/i.test(file.name)){notice('文件不支持，请选择 EPUB、PDF、TXT 或 MD。');$('ebookFile').value='';return;}if(!online||!runnerAvailable)return;const generation=invalidateRequests();requestBusy=true;$('ebookUpload').disabled=true;notice('正在上传正文…');try{const focus=$('ebookFocus').value.trim(),response=await api('/api/jobs?name='+encodeURIComponent(file.name)+(focus?'&focus='+encodeURIComponent(focus):''),{method:'POST',body:file,headers:{'Content-Type':'application/octet-stream'}});if(generation!==requestGeneration)return;showJob(response.job);notice('文件已接收，正在处理。');}catch(e){if(generation===requestGeneration){notice('上传失败：'+e.message);if(job)showJob(job);else $('ebookUpload').disabled=false;}}finally{requestBusy=false;$('ebookFile').value='';}};
    for(const action of ['cancel','retry','approve'])if($('ebook'+action[0].toUpperCase()+action.slice(1)))$('ebook'+action[0].toUpperCase()+action.slice(1)).onclick=async()=>{if(!job||requestBusy)return;const id=job.id,generation=invalidateRequests();requestBusy=true;try{const response=await api('/api/jobs/'+encodeURIComponent(id)+'/'+action,{method:'POST'});if(generation===requestGeneration&&job?.id===id&&response.job?.id===id)showJob(response.job);}catch(e){if(generation===requestGeneration&&job?.id===id){notice('操作失败：'+e.message);showJob(job);}}finally{requestBusy=false;titleEnabled();}};
    if($('ebookReconnect'))$('ebookReconnect').onclick=connect;
    if($('ebookStartInstruction'))$('ebookStartInstruction').onclick=()=>{if(job?.state==='awaiting_agent')copy('开始蒸馏年年阅任务 '+job.id+'。工作台输出目录：'+config.output+'。请使用当前会话的模型，按年年阅 Skill 的当前 Agent 交接流程处理。');};
    async function copy(text){try{if(navigator.clipboard?.writeText)await navigator.clipboard.writeText(text);else{const field=el('textarea',text);field.style.position='fixed';field.style.opacity='0';document.body.append(field);field.select();const ok=document.execCommand('copy');field.remove();if(!ok)throw Error('浏览器未授权复制');}notice('已复制');}catch(e){notice('复制失败：'+e.message+'。可下载 Markdown 保存全文。');}}
    function download(blob,name){const url=URL.createObjectURL(blob),link=el('a');link.href=url;link.download=name;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),30000);}
    $('ebookCopyAll').onclick=()=>copy(digestText());$('ebookDownloadMd').onclick=()=>download(new Blob([digestText()],{type:'text/markdown;charset=utf-8'}),safeName()+'.md');
    $('ebookDownloadHtml').onclick=async()=>{try{
      let page;
      {
        const section=root.cloneNode(true);delete section.dataset.mounted;section.dataset.readerMode='readonly';
        section.querySelector('.ebook-upload-area')?.remove();section.querySelector('#ebookTask')?.remove();
        section.querySelector('#ebookBookPicker')?.remove();section.querySelector('#ebookEmpty')?.remove();
        section.querySelector('#ebookResult').replaceChildren();
        section.querySelector('#ebookResultShell').hidden=true;
        const styles=[...document.querySelectorAll('style')].map(s=>s.outerHTML).join('\n'),scripts=[...document.scripts].filter(s=>s.id==='ebook-app-mounted'||s.id==='reading-share-mounted'||s.textContent.startsWith('/* Editorial share artwork.')).map(s=>s.outerHTML).join('\n'),safe=JSON.stringify({analysis:result.analysis,digest:digestText(),source_mode:result.source_mode}).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
        page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>年年阅 · 书籍精华</title>'+styles+'<script>window.EBOOK_RESULT='+safe+';<'+'/script></head><body class="ebook-standalone"><div class="paper"><main>'+section.outerHTML+'</main></div>'+scripts+'</body></html>';
      }
      download(new Blob([page],{type:'text/html;charset=utf-8'}),safeName()+'.html');notice('独立 HTML 已导出，可离线阅读。');
    }catch(e){notice('导出失败：'+e.message);}};
    if($('ebookBookSelect')){const select=$('ebookBookSelect');bundles.forEach((b,i)=>{const option=el('option',(b.analysis.book.title||'未命名书籍')+(b.analysis.book.author?' · '+b.analysis.book.author:''));option.value=String(i);select.append(option);});$('ebookBookPicker').hidden=bundles.length<2;select.onchange=()=>{if(!bundles[Number(select.value)])return;result=bundles[Number(select.value)];notice('');renderResult();};}
    if(result)renderResult();else if($('ebookEmpty'))$('ebookEmpty').hidden=false;
    if(!readonly)connect();
  };
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount,{once:true});else mount();
})();
