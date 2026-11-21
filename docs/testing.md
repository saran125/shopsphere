# Testing and acceptance checklist

Run the unit and importer tests from the project root:

```powershell
py -3 -m pytest shopsphere\tests
```

The MongoDB integration test is skipped unless `MONGODB_TEST_URI` is set. Run
it against a local MongoDB server with:

```powershell
$env:MONGODB_TEST_URI = "mongodb://127.0.0.1:27017"
py -3 -m pytest shopsphere\tests
Remove-Item Env:\MONGODB_TEST_URI
```

The integration test writes to and drops a uniquely named temporary database;
it does not alter the application's `shopsphere` database. `shopsphere\db\mongodb.js`
sets MongoDB schema validators and indexes for the application collections.

Run `py -3 -m shopsphere.scripts.verify` to verify the demo stores without
external services.

Manual acceptance:

1. Start the app in demo mode and confirm the demo accounts, catalog, cart,
   checkout, seller stock management, image upload, and admin analytics work.
2. Start the MongoDB container, set `APP_MODE=mongodb`, and confirm app startup
   fails visibly if MongoDB is unavailable rather than falling back to memory.
3. In MongoDB mode, add a product review and browse products; confirm reviews
   and browsing events persist after restarting the app.
4. Import the representative Olist sample and confirm source products have
   zero inventory, source specifications persist in MongoDB, and order-level
   Olist review summaries remain separate from ShopSphere product ratings.
5. Place a simulated order and confirm checkout remains a relational-database
   transaction.
