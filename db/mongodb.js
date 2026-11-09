use('shopsphere');
db.createCollection('Reviews');
db.createCollection('BrowsingHistory');
db.createCollection('ProductSpecifications');
db.Reviews.createIndex({product_id: 1, user_id: 1}, {unique: true});
db.BrowsingHistory.createIndex({user_id: 1, timestamp: -1});
db.BrowsingHistory.createIndex({product_id: 1, event_type: 1});
db.ProductSpecifications.createIndex({product_id: 1}, {unique: true});
