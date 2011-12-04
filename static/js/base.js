$(document).ready(function () {
    $('#title').click(function () {
        window.location = '/';
    });
    $('.graff_img').click(function () {
        full = this.src.replace(/\.[a-z]*$/, '.o');
        window.location = full;
    });
});
