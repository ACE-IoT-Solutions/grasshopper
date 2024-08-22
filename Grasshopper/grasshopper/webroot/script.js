const host = window.location.protocol + '//' + window.location.host;

console.log(host);

document.addEventListener("DOMContentLoaded", function() {
    const imageElement = document.getElementById('cameraImage');
    const sidemenu = document.querySelector('.sidemenu');
    let currentSelectedButton = null; 

    sidemenu.addEventListener('click', function(e) {
        if (e.target.tagName === 'BUTTON') {
            const imageUrl = e.target.getAttribute('data-img-src');
            imageElement.src = imageUrl;
            imageElement.setAttribute('data-original-src', imageUrl);
            
            if (currentSelectedButton) {
                currentSelectedButton.style.backgroundColor = "";
            }
            e.target.style.backgroundColor = "green";
            currentSelectedButton = e.target;
        }
    });

    fetch(host + '/grasshopper_rpc/jsonrpc')
    .then(response => response.json())
    .then(data => {
        const cameras = data.data;
        cameras.forEach(camera => {
            const btn = document.createElement('button');
            btn.textContent = camera.name;
            btn.setAttribute('data-img-src', host + camera.src);
            sidemenu.appendChild(btn);
        });
        
        const firstButton = sidemenu.querySelector('button');
        if (firstButton) {
            firstButton.click();
        }
    })
    .catch(error => {
        console.error("Error fetching camera data:", error);
    });

    function refreshImage() {
        const originalSrc = imageElement.getAttribute('data-original-src');
        if (originalSrc) {
            const refreshedSrc = originalSrc + '?timestamp=' + new Date().getTime();
            imageElement.src = refreshedSrc;
        }
    }

    setInterval(refreshImage, 5000);
});
