/* Service worker do Dimensionador S2V.
 *
 * Para que serve: permitir instalar o programa como aplicativo (ícone na tela
 * do celular) e abri-lo em tela cheia, sem a barra do navegador.
 *
 * Cuidado importante: este service worker NÃO guarda em cache as respostas de
 * cálculo, conferência, PDF nem QR — essas têm de vir sempre novas do servidor,
 * senão o app mostraria contas velhas. Ele só guarda a "casca" (a página e os
 * ícones) para o app abrir rápido e, se faltar sinal por um instante, ainda
 * exibir a tela. Toda conta continua sendo feita no servidor.
 */
const VERSAO = 's2v-v1';                 // troque para 's2v-v2' etc. ao mudar a casca
const CASCA = [
  '/',
  '/manifest.webmanifest',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/logo.png'
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(VERSAO).then((c) => c.addAll(CASCA)).catch(() => {}));
  self.skipWaiting();                    // ativa a versão nova sem esperar
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((chaves) => Promise.all(
        chaves.filter((k) => k !== VERSAO).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  const url = new URL(req.url);

  // Passa direto para a rede (nunca cacheia): tudo que não é GET, outro domínio,
  // as rotas de API, a geração de PDF e o QR. São coisas dinâmicas.
  if (req.method !== 'GET' ||
      url.origin !== location.origin ||
      url.pathname.startsWith('/api/') ||
      url.pathname === '/qr.png') {
    return;                             // deixa o navegador tratar (sempre rede)
  }

  // Abrir a página (navegação): tenta a rede primeiro (para pegar a versão mais
  // nova) e só cai no cache se estiver sem conexão.
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(VERSAO).then((c) => c.put('/', copia)).catch(() => {});
          return resp;
        })
        .catch(() => caches.match('/').then((r) => r || caches.match(req)))
    );
    return;
  }

  // Ícones, logo, manifesto: usa o cache na hora e atualiza em segundo plano.
  e.respondWith(
    caches.match(req).then((cacheado) => {
      const rede = fetch(req)
        .then((resp) => {
          const copia = resp.clone();
          caches.open(VERSAO).then((c) => c.put(req, copia)).catch(() => {});
          return resp;
        })
        .catch(() => cacheado);
      return cacheado || rede;
    })
  );
});
