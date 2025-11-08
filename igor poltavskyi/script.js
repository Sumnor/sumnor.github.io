(function() {
  const currentScript = document.currentScript;
  const fileName = currentScript.getAttribute('data-file');
  const targetId = currentScript.getAttribute('data-target'); 
  const filePath = `text/${fileName}`;
  const element = document.getElementById(targetId);

  if (!element) return;

  fetch(filePath)
    .then(res => {
      if (!res.ok) throw new Error('File not found: ' + filePath);
      return res.text();
    })
    .then(text => {
      text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
      text = text.replace(/\*(.*?)\*/g, '<em>$1</em>');
      text = text.replace(/\n/g, '<br>');
      element.innerHTML = text;
    })
    .catch(err => {
      element.textContent = 'Failed to load text.';
      console.error(err);
    });
})();
