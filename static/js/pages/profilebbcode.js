function toggleSpoilerBox(boxId) {
    var spoilerbox = document.getElementById(boxId);
    var spoilerContent = spoilerbox.querySelector('.spoilerbox-content');
    
    if (spoilerContent.style.display === "none") {
        spoilerContent.style.display = "block";
    } else {
        spoilerContent.style.display = "none";
    }
}