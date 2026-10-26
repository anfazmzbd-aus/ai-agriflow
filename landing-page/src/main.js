const dialog = document.querySelector('#detail');
const details = {
 crop: ['CROP HEALTH AGENT', 'Understand what your crops are telling you.', 'The proposed crop health agent helps interpret plant observations and images to surface possible signs of stress or disease. Its goal is to make early investigation easier. Findings are advisory and should be checked with local agricultural expertise.'],
 weather: ['WEATHER ADVISORY AGENT', 'Turn the forecast into a farm plan.', 'The proposed weather agent connects local forecasts with crop context to support decisions about field work, planting, and irrigation. The weather shown on this page is illustrative, rather than a live forecast.'],
 soil: ['SOIL & RESOURCE AGENT', 'Make every input more intentional.', 'The proposed resource agent combines the soil and crop information a farmer provides to help explore water and nutrient needs. Recommendations would depend on reliable field data and local conditions.'],
 overview: ['AI AGENT CAPSTONE PROJECT', 'One connected vision for smarter agriculture.', 'AI AgriFlow is a capstone concept for a collaborative agricultural AI agent platform. Crop health, weather advisory, and soil and resource agents are designed to bring useful insights into one place. This landing page introduces that vision; live analysis and farm integrations are not connected yet.']
};
function openDetail(key) { const [label, title, copy] = details[key]; document.querySelector('#detail-label').textContent = label; document.querySelector('#detail-title').textContent = title; document.querySelector('#detail-copy').textContent = copy; dialog.showModal(); }
document.querySelectorAll('[data-agent]').forEach(button => button.addEventListener('click', () => openDetail(button.dataset.agent)));
document.querySelector('#open-overview').addEventListener('click', () => openDetail('overview'));
document.querySelectorAll('.close, #dialog-done').forEach(button => button.addEventListener('click', () => dialog.close()));
dialog.addEventListener('click', event => { if (event.target === dialog) { const r = dialog.getBoundingClientRect(); if(event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) dialog.close(); } });
const menu = document.querySelector('.menu');
menu.addEventListener('click', () => { const expanded = menu.getAttribute('aria-expanded') !== 'true'; menu.setAttribute('aria-expanded', String(expanded)); document.querySelector('nav').classList.toggle('open', expanded); });
document.querySelectorAll('nav a').forEach(link => link.addEventListener('click', () => { menu.setAttribute('aria-expanded', 'false'); document.querySelector('nav').classList.remove('open'); }));
document.querySelector('#year').textContent = new Date().getFullYear();
