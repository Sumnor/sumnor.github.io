// ----------------------
// IndexedDB Setup
// ----------------------
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open("PNWStore", 2);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;

            if (!db.objectStoreNames.contains("nations")) {
                db.createObjectStore("nations", { keyPath: "id" });
            }

            if (!db.objectStoreNames.contains("alliances")) {
                db.createObjectStore("alliances", { keyPath: "id" });
            }
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}


// ----------------------
// Saving + Loading
// ----------------------
async function saveToDB(storeName, items) {
    const db = await openDB();
    const tx = db.transaction(storeName, "readwrite");
    const store = tx.objectStore(storeName);

    for (const item of items) {
        store.put(item);
    }

    return tx.complete;
}

async function loadFromDB(storeName) {
    const db = await openDB();
    const tx = db.transaction(storeName, "readonly");
    const store = tx.objectStore(storeName);

    return new Promise((resolve) => {
        const result = [];
        store.openCursor().onsuccess = (e) => {
            const cursor = e.target.result;
            if (cursor) {
                result.push(cursor.value);
                cursor.continue();
            } else {
                resolve(result);
            }
        };
    });
}


// ----------------------
// API Fetch + Cache Logic
// ----------------------
async function fetchWithCache(apiUrl, storeName) {
    const lastUpdateKey = "lastUpdate_" + storeName;
    const lastUpdate = Number(localStorage.getItem(lastUpdateKey) || 0);
    const now = Date.now();

    if (now - lastUpdate < 15 * 60 * 1000) {
        return loadFromDB(storeName);
    }

    const res = await fetch(apiUrl);
    const data = await res.json();

    await saveToDB(storeName, data);
    localStorage.setItem(lastUpdateKey, now);

    return data;
}


// ----------------------
// Render UI
// ----------------------
function renderNations(nations) {
    const container = document.getElementById("nations-list");
    container.innerHTML = "";

    nations.forEach(n => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            <h3>${n.name}</h3>
            <p>Leader: ${n.leader}</p>
            <p>Score: ${n.score}</p>
        `;
        container.appendChild(card);
    });
}

function renderAlliances(alliances) {
    const container = document.getElementById("alliances-list");
    container.innerHTML = "";

    alliances.forEach(a => {
        const card = document.createElement("div");
        card.className = "card";
        card.innerHTML = `
            <h3>${a.name}</h3>
            <p>Members: ${a.members}</p>
            <p>Rank: ${a.rank}</p>
        `;
        container.appendChild(card);
    });
}


// ----------------------
// Tab Switcher
// ----------------------
document.getElementById("tab-nations").addEventListener("click", () => {
    document.getElementById("nations-section").classList.add("active");
    document.getElementById("alliances-section").classList.remove("active");

    document.getElementById("tab-nations").classList.add("active");
    document.getElementById("tab-alliances").classList.remove("active");
});

document.getElementById("tab-alliances").addEventListener("click", () => {
    document.getElementById("alliances-section").classList.add("active");
    document.getElementById("nations-section").classList.remove("active");

    document.getElementById("tab-alliances").classList.add("active");
    document.getElementById("tab-nations").classList.remove("active");
});


// ----------------------
// Initialization
// ----------------------
(async () => {
    const nations = await fetchWithCache("/api/nations", "nations");
    renderNations(nations);

    const alliances = await fetchWithCache("/api/alliances", "alliances");
    renderAlliances(alliances);
})();
