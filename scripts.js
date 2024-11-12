// JavaScript for modal pop-up and follow functionality
document.addEventListener('DOMContentLoaded', function () {
    // Follow/Unfollow functionality
    const userSuggestions = document.getElementById('user-suggestions');
    userSuggestions.addEventListener('click', function (e) {
        if (e.target && e.target.nodeName === 'BUTTON') {
            const button = e.target;
            if (button.classList.contains('following')) {
                // Unfollow
                button.textContent = 'Follow';
                button.classList.remove('following');
                button.style.backgroundColor = '#f44336';
            } else {
                // Follow
                button.textContent = 'Following';
                button.classList.add('following');
                button.style.backgroundColor = 'green';
                // Display pop-up notification
                alert(`You are now following ${button.dataset.username}`);
            }
        }
    });

    // Modal for creating a new post
    const createPostButton = document.getElementById('create-post-button');
    const modal = document.getElementById('post-modal');
    const closeModal = document.getElementById('close-modal');

    createPostButton.addEventListener('click', function () {
        modal.style.display = 'block';
    });

    closeModal.addEventListener('click', function () {
        modal.style.display = 'none';
    });

    window.addEventListener('click', function (e) {
        if (e.target === modal) {
            modal.style.display = 'none';
        }
    });
});
