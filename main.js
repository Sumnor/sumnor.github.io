// ================================
// IndexedDB Helpers
// ================================
function openDB() {
    return new Promise((resolve, reject) => {
        const request = indexedDB.open("PNWDatabase", 1);

        request.onupgradeneeded = (event) => {
            const db = event.target.result;
            if (!db.objectStoreNames.contains("nations")) {
                db.createObjectStore("nations", { keyPath: "id" });
            }
        };

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function saveNationsToIndexedDB(nations) {
    const db = await openDB();
    const tx = db.transaction("nations", "readwrite");
    const store = tx.objectStore("nations");

    for (const nation of nations) {
        store.put(nation);
    }

    return tx.complete;
}

async function loadNationsFromIndexedDB() {
    const db = await openDB();
    const tx = db.transaction("nations", "readonly");
    const store = tx.objectStore("nations");

    return new Promise((resolve) => {
        const result = [];
        const cursor = store.openCursor();

        cursor.onsuccess = (event) => {
            const cur = event.target.result;
            if (cur) {
                result.push(cur.value);
                cur.continue();
            } else {
                resolve(result);
            }
        };
    });
}


// ================================
// Fetch + Cache Logic
// ================================

const UPDATE_INTERVAL_MS = 15 * 60 * 1000; // 15 minutes
const API_URL = "https://your-api-url-here.com/nations"; 
// Replace with your API endpoint


async function fetchAndCacheNations() {
    const lastUpdate = Number(localStorage.getItem("lastUpdate")) || 0;
    const now = Date.now();

    // Use cached if fresh
    if (now - lastUpdate < UPDATE_INTERVAL_MS) {
        console.log("Using cached data.");
        return loadNationsFromIndexedDB();
    }

    // Fetch new data
    console.log("Fetching new data from API:", API_URL);
    document.getElementById("status").innerText = "Fetching latest data...";

    const response = await fetch(API_URL);
    const nations = await response.json();

    // Save new data
    await saveNationsToIndexedDB(nations);
    localStorage.setItem("lastUpdate", now);

    return nations;
}


// ================================
// App Logic
// ================================

async function main() {
    const nations = await fetchAndCacheNations();
    
    document.getElementById("status").innerText = 
        `Loaded ${nations.length} nations`;

    document.getElementById("output").innerText = 
        JSON.stringify(nations.slice(0, 10), null, 2) + 
        "\n\n(Showing first 10 for preview)";
}

main();
