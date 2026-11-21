// Esconde o botão do topo enquanto o botão grande do início está na tela.
(function () {
  var alvo = document.getElementById('baixar-hero');
  var raiz = document.documentElement;
  if (!alvo || !('IntersectionObserver' in window)) return;
  new IntersectionObserver(function (es) {
    raiz.classList.toggle('no-topo', es[0].isIntersecting);
  }, { rootMargin: '-60px 0px 0px 0px' }).observe(alvo);
})();

// Caixinha de apoio: fecha com Esc ou clicando fora.
(function () {
  var d = document.getElementById('apoio');
  if (!d) return;
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && d.open) { d.open = false; d.querySelector('summary').focus(); } });
  document.addEventListener('click', function (e) { if (d.open && !d.contains(e.target)) d.open = false; });
  var b = document.getElementById('copiar-pix');
  if (!b) return;
  b.addEventListener('click', function () {
    var cod = b.getAttribute('data-pix');
    function ok() { b.textContent = 'Copiado ✓'; setTimeout(function () { b.textContent = 'Copiar Pix copia e cola'; }, 2500); }
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(cod).then(ok, function () { window.prompt('Copie o código Pix:', cod); });
    else window.prompt('Copie o código Pix:', cod);
  });
})();

// Vídeo do início: toca mudo uma vez e para no último quadro; o botão liga o som e recomeça. Sem JS, ficam os controles do navegador.
(function () {
  var v = document.getElementById('video-hero');
  var b = document.getElementById('som-hero');
  if (!v || !b) return;
  var calmo = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (calmo) { v.removeAttribute('autoplay'); v.pause(); return; }   // mantém os controles
  v.removeAttribute('controls');
  b.hidden = false;
  var txt = b.querySelector('span');
  var FINAL = 21.2;     // quadro do encerramento já montado (o último segundo é o escurecimento)
  var acabou = false;
  function tocar() {
    if (acabou) { acabou = false; v.currentTime = 0; }
    v.play();
  }
  v.addEventListener('ended', function () { acabou = true; v.currentTime = FINAL; });
  b.addEventListener('click', function () {
    v.muted = !v.muted;
    if (!v.muted) { acabou = false; v.currentTime = 0; v.play(); }
    b.setAttribute('aria-pressed', String(!v.muted));
    txt.textContent = v.muted ? 'Ativar som' : 'Som ligado';
  });
  v.addEventListener('click', function () { if (v.paused) tocar(); else v.pause(); });
})();
