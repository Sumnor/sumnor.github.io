const fileList = document.getElementById('thesis-file-list');
const THESIS_FOLDER_PATH = '/thesis/'; 
const PATH_CLEANUP_REGEX = new RegExp(`^${THESIS_FOLDER_PATH.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&')}`);

function extractFileNamesFromHtml(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    const fileNames = [];
    const normalizedFolderPath = THESIS_FOLDER_PATH.replace(/\/\/+/g, '/').toLowerCase();
    
    doc.querySelectorAll('a').forEach(link => {
        let fileName = link.getAttribute('href');
        
        if (fileName) {
            let decodedFileName = decodeURIComponent(fileName);
            let lowerCaseFileName = decodedFileName.toLowerCase();

            if (lowerCaseFileName.startsWith('?') || lowerCaseFileName.startsWith('.') || lowerCaseFileName === '../' || lowerCaseFileName === '/' || lowerCaseFileName.endsWith('/')) {
                return; 
            }
            
            if (lowerCaseFileName === normalizedFolderPath.replace(/\/$/, '')) {
                return; 
            }

            fileNames.push(decodedFileName);
        }
    });
    return Array.from(new Set(fileNames)).sort();
}

function renderThesisList(fileNames) {
    fileList.innerHTML = ''; 

    if (fileNames.length === 0) {
        fileList.innerHTML = '<li>No thesis documents found in the directory.</li>';
        return;
    }

    fileNames.forEach(fileName => {
        let nameWithoutExt = fileName.replace(/\.[^/.]+$/, "");
        
        nameWithoutExt = nameWithoutExt.replace(PATH_CLEANUP_REGEX, '').replace(/^\/+/g, '');
        const linkUrl = new URL(fileName, window.location.origin + THESIS_FOLDER_PATH).href;
        
        const listItem = document.createElement('li');
        const link = document.createElement('a');

        link.href = linkUrl;
        link.classList.add('thesis-link');
        
        link.textContent = nameWithoutExt.replace(/_/g, ' '); 
        
        listItem.appendChild(link);
        fileList.appendChild(listItem);
    });
}

fetch(THESIS_FOLDER_PATH)
    .then(response => {
        if (!response.ok) {
            throw new Error(`Failed to fetch directory index. Status: ${response.status}`);
        }
        return response.text();
    })
    .then(html => {
        const fileNames = extractFileNamesFromHtml(html);
        renderThesisList(fileNames);
    })
    .catch(error => {
        console.error('Error fetching directory listing:', error);
        fileList.innerHTML = `<li>Error: Could not list documents. Directory Indexing may be disabled on the server for the "${THESIS_FOLDER_PATH}" folder.</li>
                              <li>You must either enable indexing or use a server-side language (PHP) to generate the list.</li>`;
    });