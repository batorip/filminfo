let originalRows = [];  // Az eredeti sorrend mentése
let isSorted = false;   // Nyomon követi, hogy rendezve van-e

document.addEventListener("DOMContentLoaded", () => {
    let table = document.querySelector("table");
    originalRows = Array.from(table.querySelectorAll("tr")); // Eredeti mentése

    // Lokalizált szövegek beolvasása
    textSort = document.getElementById("sortTextSort").textContent;
    textOriginal = document.getElementById("sortTextOriginal").textContent;

    document.getElementById("sortButton").textContent = textSort;
});

let colgroup = null;

function getColgroup() {
    let table = document.querySelector("table");
    colgroup = table.querySelector("colgroup");  // Mentjük el a colgroup elemet
}
function sortTableByDate() {
    let table = document.querySelector("table");
    let button = document.getElementById("sortButton");

    if (!colgroup) {
        getColgroup();
    }

    if (isSorted) {
        // 🔄 **Visszaállítjuk az eredeti sorrendet**
        table.innerHTML = "";
        if (colgroup) {  // Hozzáadjuk a colgroup-ot a táblázathoz
            table.appendChild(colgroup);
        }
        originalRows.forEach(row => table.appendChild(row));
        button.textContent = textSort;
        isSorted = false;
    } else {
        // 📅 **Rendezés dátum szerint**
        let rows = Array.from(table.querySelectorAll("tr"));
        let groupedRows = [];
        let currentGroup = [];

        rows.forEach((row) => {
            currentGroup.push(row);

            if (row.querySelector(".download_date")) {
                let dateCell = row.querySelector(".download_date");
                let dateText = dateCell.textContent.trim();
                let timestamp = Date.parse(dateText);

                if (!isNaN(timestamp)) {
                    groupedRows.push({ timestamp, rows: [...currentGroup] });
                } else {
                    console.warn("Érvénytelen dátum:", dateText);
                }

                currentGroup = [];
            }
        });

        // **Rendezés dátum szerint csökkenő sorrendben (legújabb elöl)**
        groupedRows.sort((a, b) => b.timestamp - a.timestamp);

        // **Táblázat frissítése az új sorrenddel**
        table.innerHTML = "";
        if (colgroup) {  // Hozzáadjuk a colgroup-ot a táblázathoz
            table.appendChild(colgroup);
        }
        groupedRows.forEach(group => {
            group.rows.forEach(row => table.appendChild(row));
        });

        button.textContent = textOriginal;
        isSorted = true;
    }
    console.log("Táblázat rendezve:", isSorted ? "Dátum szerint" : "Eredeti sorrend");
}
