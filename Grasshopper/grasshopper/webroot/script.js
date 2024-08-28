const host = window.location.protocol + '//' + window.location.host;

console.log(host);

document.addEventListener('DOMContentLoaded', function() {
    // Fetch available graphs on page load
    fetchAvailableGraphs();
});

function fetchAvailableGraphs() {

    fetch(host + '/grasshopper_rpc/jsonrpc')
    .then(response => response.json())
    .then(data => {
        if (data.data) {
            console.log(data.data)
            populateGraphSelector(data.data);
        } else {
            console.error('Error fetching graphs:', data.error);
        }
    })
    .catch(error => console.error('Fetch error:', error));
}

function populateGraphSelector(graphs) {
    const selector = document.getElementById('graph-selector');
    graphs.forEach(graph => {
        const option = document.createElement('option');
        let datePart = graph.split('_')[2];
        option.value = host+"/grasshopper/graphs/html/" + graph;
        option.text = datePart;
        selector.appendChild(option);
    });
}

function showSelectedGraph() {
    const selector = document.getElementById('graph-selector');
    const selectedGraph = selector.value;
    if (selectedGraph) {
        document.getElementById('graph-frame').src = selectedGraph;
    }
}

function goToHtmlGraph() {
    const selector = document.getElementById('graph-selector');
    const selectedLink = selector.value;
    
    if (selectedLink) {
        window.open(selectedLink, '_blank');
    } else {
        alert("Please select a link from the dropdown menu.");
    }
}

function goToTtlGraph() {
    const selector = document.getElementById('graph-selector');
    const selectedLink = selector.value;
    
    if (selectedLink) {
        updatedLink = selectedLink.replace(/html/g, "ttl");
        window.open(updatedLink, '_blank');
    } else {
        alert("Please select a link from the dropdown menu.");
    }
}
