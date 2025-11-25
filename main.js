async function loadJSONL(url) {
    const res = await fetch(url);
    const text = await res.text();

    return text
        .trim()
        .split("\n")
        .map(line => JSON.parse(line));
}

function render(data) {
    const out = document.getElementById("output");
    out.innerHTML = "";

    data.forEach(n => {
        const div = document.createElement("div");
        div.className = "nation";

        div.innerHTML = `
            <strong>${n.nation_name}</strong><br>
            ID: ${n.id}<br>
            Score: ${n.score ?? "N/A"}<br>
            Population: ${n.population ?? "N/A"}
        `;

        out.appendChild(div);
    });
}

function sortData(data, key) {
    return data.sort((a, b) => {
        const A = a[key] ?? 0;
        const B = b[key] ?? 0;

        if (typeof A === "string") return A.localeCompare(B);
        return A - B;
    });
}

async function main() {
    // Update this path to your GitHub raw link
    const url = "https://raw.githubusercontent.com/USERNAME/REPO/main/nations.jsonl";

    let nations = await loadJSONL(url);

    const select = document.getElementById("sortSelect");

    function update() {
        const sorted = sortData([...nations], select.value);
        render(sorted);
    }

    select.addEventListener("change", update);
    update();
}

main();
