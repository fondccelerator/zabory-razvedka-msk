// Similarweb Pro: перехват ответов виджетов страницы сравнения (Website performance, до 5 доменов).
// Порядок (20.10.2026 сработало):
// 1) navigate на https://pro.similarweb.com/#/digitalsuite/websiteanalysis/overview/website-performance/*/999/3m?webSource=Total&key=d1,d2,d3,d4,d5
//    (страна 643 и период 12m пробный доступ не даёт: редирект на 999 и 3m)
// 2) через javascript_tool выполнить блок ниже: он повторно запрашивает URL виджетов, уже загруженных страницей
//    (подписанные URL; собственные запросы с другими параметрами получают 403 от CloudFront)
// 3) читать window.out кусками ch(0), ch(1)... (вывод инструмента обрезается около 1000 знаков;
//    знаки = ; & ? в выводе блокируются фильтром, поэтому clean())
// Лимит пробного доступа: после ~8 просмотров страниц за день — окно «Daily usage limit reached».
// Один просмотр сравнения на 5 доменов даёт: визиты, помесячно, вовлечённость, устройства, каналы (визиты), соцсети, топ-5 ключей и рефералов группы.

performance.setResourceTimingBufferSize(10000);
window.CAP = [];
window.clean = s => s.replace(/=/g, ':').replace(/;/g, ' ').replace(/[&?]/g, ' ');
window.r3 = x => x == null ? '' : Math.round(x * 1000) / 1000;
window.r0 = x => x == null ? '' : Math.round(x);
window.J = s => { const out = []; CAP.filter(c => c.url.includes(s)).forEach(x => { try { out.push({ u: new URL(x.url, location.origin), j: JSON.parse(x.t) }) } catch (e) { } }); return out; };
const ents = performance.getEntriesByType('resource').map(e => e.name).filter(n => /widgetApi/.test(n));
for (const n of ents) {
  try {
    const r = await fetch(n, { credentials: 'include', headers: { accept: 'application/json', 'x-requested-with': 'XMLHttpRequest' } });
    CAP.push({ url: n, t: await r.text(), s: r.status });
  } catch (e) { }
}
window.ovc = () => {
  const L = [];
  const g = s => { const a = J(s).filter(x => !x.u.pathname.endsWith('Pop')); return a.length ? a[a.length - 1].j : null };
  const ev = g('EngagementVisits/Table'), dm = g('EngagementDesktopVsMobileVisits'), eo = g('EngagementOverview'), gr = g('EngagementVisits/Graph'),
    mm = g('MarketingMixTotal/TrafficSourcesOverview/PieChart'), so = g('TrafficSourcesSocial'), rf = g('TopReferrals');
  (ev.Data || []).forEach(d => {
    const D = d.Domain; const e = (eo && eo.Data || []).find(x => x.Domain == D) || {};
    const v = k => e[k] == null ? null : (typeof e[k] == 'object' ? e[k].Value : e[k]);
    const m = (dm && dm.Data || []).find(x => x.Domain == D) || {};
    const gg = gr && gr.Data && gr.Data[D] ? gr.Data[D].Total[0].map(p => p.Key.slice(0, 7) + ':' + r0(p.Value)).join(',') : '';
    L.push(['OV', D, r0(d.TotalVisits), r3(d.Change), gg, r0(v('AvgMonthVisits')), r0(v('UniqueUsers')), r0(v('DedupUniqueUsers')), r0(v('AvgVisitDuration')), r3(v('PagesPerVisit')), r3(v('BounceRate')), (m.DesktopMobileShareVisits || []).map(r3).join('/')].join('|'));
  });
  if (mm && mm.Data && mm.Data.Total) Object.entries(mm.Data.Total).forEach(([D, c]) => L.push('CH|' + D + '|' + Object.entries(c).map(([k, x]) => k + ':' + r0(x)).join(' ')));
  if (so && so.Data) Object.entries(so.Data).forEach(([D, c]) => L.push('SO|' + D + '|' + Object.entries(c).map(([k, x]) => k + ':' + r3(x.Share)).join(' ')));
  if (rf && rf.Data) L.push('REFG|' + rf.Data.map(x => x.Domain + ':' + r3(x.Share) + '[' + (x.ShareList || []).map(r3).join('/') + ']').join(' '));
  J('SearchKeywordsV2').forEach(x => L.push('KWG' + (x.u.searchParams.get('SourceType') || '')[0] + '|' + (x.j.Data || []).map(k => k.SearchTerm + '~' + r3(k.TotalShare) + '~' + k.TotalVisits + '~' + JSON.stringify(k.SiteOrigins).replace(/[{}"]/g, '') + '~cpc' + r3(k.CPC) + '~vol' + k.KwVolume).join(' ;; ')));
  return clean(L.join('\n'));
};
window.out = ovc(); window.ch = i => out.slice(i * 900, (i + 1) * 900);
out.length + '\n' + ch(0);

// Полный список ключей одного домена (100 на страницу, клики organic/paid, частотность, CPC):
//   #/organicsearch/pageAnalysis/website-keyword-v2/*/999/3m?webSource=Total&key=<домен>  -> widgetApi/WebsiteAnalysisV2/WebsiteAnalysis/Table, Data.Records
// Брендовый/небрендовый поиск и платный/органический за 3 мес:
//   #/digitalsuite/websiteanalysis/search-overview/*/999/3m?webSource=Total&key=<домен> -> api/searchoverview/overview/traffic, keywords/brand-split, overview/top-keywords
// Все ссылающиеся домены с визитами:
//   #/digitalsuite/websiteanalysis/referrals/*/999/3m?webSource=Total&key=<домен> -> api/websiteanalysis/GetTrafficSourcesTotalReferralsTable, Records
// Медийная реклама (площадки, показы, модельный бюджет):
//   #/digitalsuite/websiteanalysis/display-overview/*/999/3m?webSource=Total&key=<домен> -> api/AdIntelligence/Advertiser/PerformanceOverviewV2/unified, Publishers/breakdown
