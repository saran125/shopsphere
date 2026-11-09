# Testing and acceptance checklist

`python -m pytest tests -q` verifies authentication, cart checkout,
transaction empty-cart failure, review CRUD and rating aggregation. `python -m
shopsphere.scripts.verify` checks the demo stores independently of external services.

Manual acceptance: register and log in; browse/search; add and edit cart items;
place one simulated order; log in as seller and update stock; log in as admin
and inspect analytics; save and delete a review; refresh and confirm no duplicate
checkout occurs.
