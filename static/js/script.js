const foodSearch = document.getElementById("foodSearch");
const foodCategoryFilter = document.getElementById("foodCategoryFilter");
const foodSupplierFilter = document.getElementById("foodSupplierFilter");

if (foodSearch) {
    const foodCards = document.querySelectorAll(".food-card");

    function filterFood() {
        const searchText = foodSearch.value.trim().toLocaleLowerCase();
        const category = foodCategoryFilter ? foodCategoryFilter.value : "all";
        const supplier = foodSupplierFilter ? foodSupplierFilter.value : "all";

        foodCards.forEach((card) => {
            const matchesSearch = card.textContent.toLocaleLowerCase().includes(searchText);
            const matchesCategory = category === "all" || card.dataset.category === category;
            const matchesSupplier = supplier === "all" || card.dataset.supplier === supplier;
            card.hidden = !(matchesSearch && matchesCategory && matchesSupplier);
        });
    }

    foodSearch.addEventListener("input", filterFood);
    foodCategoryFilter?.addEventListener("change", filterFood);
    foodSupplierFilter?.addEventListener("change", filterFood);
}

const inventorySearch = document.getElementById("inventorySearch");
const stockFilter = document.getElementById("stockFilter");

if (inventorySearch && stockFilter) {
    const inventoryRows = document.querySelectorAll(".inventory-row");

    function filterInventory() {
        const searchText = inventorySearch.value.trim().toLocaleLowerCase();
        const filter = stockFilter.value;

        inventoryRows.forEach((row) => {
            const matchesSearch = row.dataset.food.includes(searchText);
            const matchesFilter =
                filter === "all" ||
                row.dataset.stock === filter ||
                row.dataset.expiry === filter;

            row.hidden = !(matchesSearch && matchesFilter);
        });
    }

    inventorySearch.addEventListener("input", filterInventory);
    stockFilter.addEventListener("change", filterInventory);
}

const missionSearch = document.getElementById("missionSearch");
const missionFilter = document.getElementById("missionFilter");
const missionTypeFilter = document.getElementById("missionTypeFilter");

if (missionSearch && missionFilter) {
    const missionRows = document.querySelectorAll(".mission-row");

    function filterMissions() {
        const searchText = missionSearch.value.trim().toLocaleLowerCase();
        const filter = missionFilter.value;
        const typeFilter = missionTypeFilter ? missionTypeFilter.value : "all";

        missionRows.forEach((row) => {
            const matchesSearch = row.dataset.name.includes(searchText);
            const matchesStatus =
                filter === "all" || row.dataset.status === filter;
            const matchesType =
                typeFilter === "all" || row.dataset.type === typeFilter;

            row.hidden = !(matchesSearch && matchesStatus && matchesType);
        });
    }

    missionSearch.addEventListener("input", filterMissions);
    missionFilter.addEventListener("change", filterMissions);
    missionTypeFilter?.addEventListener("change", filterMissions);
}

const transactionSearch = document.getElementById("transactionSearch");
const transactionFilter = document.getElementById("transactionFilter");

if (transactionSearch && transactionFilter) {
    const transactionRows = document.querySelectorAll(".transaction-row");

    function filterTransactions() {
        const searchText = transactionSearch.value.trim().toLocaleLowerCase();
        const filter = transactionFilter.value;

        transactionRows.forEach((row) => {
            const matchesSearch = row.dataset.food.includes(searchText);
            const matchesFilter =
                filter === "all" || row.dataset.type === filter;

            row.hidden = !(matchesSearch && matchesFilter);
        });
    }

    const astronautSearch = document.getElementById("astronautSearch");
    const astronautMissionFilter = document.getElementById("astronautMissionFilter");

    if (astronautSearch && astronautMissionFilter) {
        const astronautRows = document.querySelectorAll(".astronaut-row");

        function filterAstronauts() {
            const searchText = astronautSearch.value.trim().toLocaleLowerCase();
            const mission = astronautMissionFilter.value;

            astronautRows.forEach((row) => {
                const matchesName = row.dataset.name.includes(searchText);
                const matchesMission = mission === "all" || row.dataset.mission === mission;
                row.hidden = !(matchesName && matchesMission);
            });
        }

        astronautSearch.addEventListener("input", filterAstronauts);
        astronautMissionFilter.addEventListener("change", filterAstronauts);
    }

    const allocationSearch = document.getElementById("allocationSearch");
    const allocationMissionFilter = document.getElementById("allocationMissionFilter");
    const allocationFoodFilter = document.getElementById("allocationFoodFilter");

    if (allocationSearch && allocationMissionFilter && allocationFoodFilter) {
        const allocationRows = document.querySelectorAll(".allocation-row");

        function filterAllocations() {
            const searchText = allocationSearch.value.trim().toLocaleLowerCase();
            const mission = allocationMissionFilter.value;
            const food = allocationFoodFilter.value;

            allocationRows.forEach((row) => {
                const matchesSearch = row.dataset.search.includes(searchText);
                const matchesMission = mission === "all" || row.dataset.mission === mission;
                const matchesFood = food === "all" || row.dataset.food === food;
                row.hidden = !(matchesSearch && matchesMission && matchesFood);
            });
        }

        allocationSearch.addEventListener("input", filterAllocations);
        allocationMissionFilter.addEventListener("change", filterAllocations);
        allocationFoodFilter.addEventListener("change", filterAllocations);
    }

    transactionSearch.addEventListener("input", filterTransactions);
    transactionFilter.addEventListener("change", filterTransactions);
}

const allocationMission = document.getElementById("missionSelect");
const allocationAstronaut = document.getElementById("astronautSelect");

if (allocationMission && allocationAstronaut) {
    const astronautOptions = Array.from(allocationAstronaut.options)
        .filter((option) => option.value !== "")
        .map((option) => option.cloneNode(true));
    const astronautPlaceholder = allocationAstronaut.options[0].cloneNode(true);

    function filterAstronauts(preserveSelection) {
        const previousAstronaut = preserveSelection
            ? allocationAstronaut.value
            : "";
        const selectedMission = allocationMission.value;

        allocationAstronaut.replaceChildren(astronautPlaceholder.cloneNode(true));

        for (const option of astronautOptions) {
            if (option.dataset.missionId === selectedMission) {
                allocationAstronaut.appendChild(option.cloneNode(true));
            }
        }

        allocationAstronaut.disabled = selectedMission === "";
        if (
            previousAstronaut &&
            Array.from(allocationAstronaut.options).some(
                (option) => option.value === previousAstronaut,
            )
        ) {
            allocationAstronaut.value = previousAstronaut;
        }
    }

    allocationMission.addEventListener("change", () => filterAstronauts(false));
    filterAstronauts(true);
}