(function() {
  const currentScript = document.currentScript;
  const fileName = currentScript.getAttribute('data-file');
  const targetId = currentScript.getAttribute('data-target');
  const filePath = `../text/${fileName}`;
  const element = document.getElementById(targetId);

  if (!element) return;

  fetch(filePath)
    .then(res => {
      if (!res.ok) throw new Error('File not found: ' + filePath);
      return res.text();
    })
    .then(text => {
      const entries = text.trim().split(/\n\s*\n/);

      const formattedBlocks = entries.map(entry => {
        const viewMatch = entry.match(/<view=(.*?)>/);
        const imageURL = viewMatch ? viewMatch[1].trim() : '';

        const textMatch = entry.match(/\|\s*(.*?)(?=\\uURL:|$)/s);
        const description = textMatch ? textMatch[1].trim() : '';

        const urlMatch = entry.match(/\\uURL:\s*(\S+)/);
        const linkURL = urlMatch ? urlMatch[1].trim() : '#';
        return `
          <div style="text-align:center; margin: 2em auto;">
            <a href="${linkURL}" target="_blank" style="text-decoration:none; color:inherit;">
              ${imageURL ? `<img src="${imageURL}" alt="" style="max-width:60%; height:auto; display:block; margin:0 auto 1em;">` : ''}
              <div style="white-space:pre-wrap; font-family:inherit; font-size:1rem; line-height:1.5;">
                ${description}
              </div>
            </a>
            <div style="margin-top:0.5em; font-size:0.9rem; color:#666;">
              <a href="${linkURL}" target="_blank">${linkURL}</a>
            </div>
          </div>
        `;
      }).join('\n');

      element.innerHTML = formattedBlocks;
    })
    .catch(err => {
      element.textContent = 'Failed to load text.';
      console.error(err);
    });
})();
