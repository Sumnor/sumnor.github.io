const fileList = document.getElementById('thesis-file-list');

const THESIS_API_URL = 'https://api.github.com/repos/Sumnor/sumnor.github.io/contents/thesis';

// The base URL for the viewer page
const VIEWER_BASE_URL = 'https://sumnor.github.io/theses_reader'; 

function renderThesisList(files) {
    if (!fileList) return;
    fileList.innerHTML = '';  

    if (files.length === 0) {
        fileList.innerHTML = '<li>No thesis documents found in the directory.</li>';
        return;
    }

    files.forEach(file => {
        let fileName = file.name;
        
        // Construct the link to the viewer page with the file name as a query parameter
        // Final link will be: https://sumnor.github.io/viewer.html?doc=DocumentName.pdf
        let linkUrl = `${VIEWER_BASE_URL}?doc=${fileName}`; 
        
        let nameWithoutExt = fileName.replace(/\.[^/.]+$/, "");
        
        nameWithoutExt = nameWithoutExt.replace(/\/\//g, '/').replace(/^\/|\/$/g, '');
        
        nameWithoutExt = nameWithoutExt.replace(/[-_]/g, ' '); 
        
        nameWithoutExt = nameWithoutExt.replace(/\s\s+/g, ' ').trim(); 

        const listItem = document.createElement('li');
        const link = document.createElement('a');

        link.href = linkUrl; 
        link.classList.add('thesis-link');
        link.target = "_blank"; 
        
        link.textContent = nameWithoutExt; 
        
        listItem.appendChild(link);
        fileList.appendChild(listItem);
    });
}

async function fetchThesisDocuments() {
    try {
        const response = await fetch(THESIS_API_URL);
        
        if (!response.ok) {
            throw new Error(`GitHub API Error: ${response.status} ${response.statusText}. Check repository path.`);
        }

        const data = await response.json();
        
        const files = data
            .filter(item => item.type === 'file')
            .sort((a, b) => a.name.localeCompare(b.name));

        renderThesisList(files); 

    } catch (error) {
        console.error("Error fetching directory listing:", error);
        fileList.innerHTML = `<li>Error: Failed to load documents. Please check your console for details.</li>`;
    }
}

fetchThesisDocuments();
