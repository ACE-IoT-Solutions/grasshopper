const host = window.location.protocol + '//' + window.location.host;

console.log(host);

let compare = false;
document.getElementById('graph-selector-2').style.visibility="hidden";
document.getElementById('compare_graphs_btn').style.visibility="hidden";

document.addEventListener('DOMContentLoaded', function() {
    // Fetch available graphs on page load
    fetchAvailableGraphs();
});

function fetchAvailableGraphs() {

    fetch(host + '/grasshopper_rpc/jsonrpc')
    .then(response => response.json())
    .then(data => {
        if (data.data) {
            // console.log(data.data)
            populateGraphSelectors(data.data);
        } else {
            console.error('Error fetching graphs:', data.error);
        }
    })
    .catch(error => console.error('Fetch error:', error));
}

function populateGraphSelectors(graphs) {
    const selector = document.getElementById('graph-selector');
    const selector2 = document.getElementById('graph-selector-2');
    graphs.forEach(graph => {
        const option = document.createElement('option');
        let parts = graph.split('_')
        let datePart = parts[parts.length - 1].split('.')[0];
        option.value = host+"/grasshopper/graphs/ttl/" + graph;
        option.text = datePart;
        selector.appendChild(option);
    });
    graphs.forEach(graph => {
        const option = document.createElement('option');
        let parts = graph.split('_')
        let datePart = parts[parts.length - 1].split('.')[0];
        option.value = host+"/grasshopper/graphs/ttl/" + graph;
        option.text = datePart;
        selector2.appendChild(option);
    });
}

function showSelectedGraph() {
    const selector = document.getElementById('graph-selector');
    const selectedGraph = selector.value.replace(/ttl/g, "html");
    if (selectedGraph) {
        document.getElementById('graph-frame').src = selectedGraph;
    }
}

function showSecondaryGraph() {
    const selector = document.getElementById('graph-selector-2');
    const selectedGraph = selector.value;
    if (selectedGraph) {
        console.log(selectedGraph);
        
        document.getElementById('graph-frame-2').src = selectedGraph;
    }
}

function goToHtmlGraph() {
    const selector = document.getElementById('graph-selector');
    const selectedLink = selector.value.replace(/ttl/g, "html");
    
    if (selectedLink) {
        window.open(selectedLink, '_blank');
    } else {
        alert("Please select a link from the dropdown menu.");
    }
}

function setCompare() {
    compare = !compare;
    if (compare) {
        document.getElementById('graph-selector-2').style.visibility="visible";
        document.getElementById('compare_graphs_btn').style.visibility="visible";
    }
    else {
        document.getElementById('graph-selector-2').style.visibility="hidden";
        document.getElementById('compare_graphs_btn').style.visibility="hidden";
    }
}

function compareHtmlGraph() {
    const selector1 = document.getElementById('graph-selector');
    const selector2 = document.getElementById('graph-selector-2');
    const selectedLink1 = selector1.value;
    const selectedLink2 = selector2.value;
    
    if (selectedLink1 && selectedLink2) {
        const data = {
            "graph1": selectedLink1.split('/').pop(),
            "graph2": selectedLink2.split('/').pop()
        };
        fetch(host + '/grasshopper_rpc/compare_rdf_graphs', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json' // Ensure the data is sent as JSON
            },
            body: JSON.stringify(data) // Convert the data object to a JSON string
        })
        .then(response => response.json())
        .then(data => {
            if (data.status) {
                console.log("Comparison successful");
                
                // Reload the page to ensure fresh data and set selector to 'compare.html'
                // window.location.reload();

                // After page reload, update the first selector value to 'compare.html'
                // selector1.text = "Comparison"
                // selector1.value = host + "/grasshopper/graphs/html/compare.html";

                // Optionally, display 'compare.html' in the iframe immediately
                document.getElementById('graph-frame').src = host + "/grasshopper/graphs/html/compare.html";
            } else {
                console.error('Error fetching graphs:', data.error);
            }
        })
        .catch(error => console.error('Fetch error:', error));
    } else {
        alert("Please select a link from the dropdown menu.");
    }    
}

function goToTtlGraph() {
    const selector = document.getElementById('graph-selector');
    const selectedLink = selector.value;
    
    if (selectedLink) {
        updatedLink = selectedLink;
        window.open(updatedLink, '_blank');
    } else {
        alert("Please select a link from the dropdown menu.");
    }
}
