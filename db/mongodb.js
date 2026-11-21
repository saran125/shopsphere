use('shopsphere');

function ensureCollection(name, validator) {
  const existing = db.getCollectionInfos({name});
  if (existing.length === 0) {
    db.createCollection(name, {validator, validationLevel: 'strict'});
  } else {
    db.runCommand({collMod: name, validator, validationLevel: 'moderate'});
  }
}

ensureCollection('Reviews', {
  $jsonSchema: {
    bsonType: 'object',
    required: ['user_id', 'product_id', 'rating', 'comment', 'created_at', 'updated_at'],
    properties: {
      user_id: {bsonType: ['int', 'long'], minimum: 0},
      product_id: {bsonType: ['int', 'long'], minimum: 1},
      rating: {bsonType: ['int', 'long'], minimum: 1, maximum: 5},
      comment: {bsonType: 'string'},
      created_at: {bsonType: 'date'},
      updated_at: {bsonType: 'date'},
      reviewer_name: {bsonType: 'string'},
      color: {bsonType: 'string'},
      is_demo: {bsonType: 'bool'}
    }
  }
});

ensureCollection('BrowsingHistory', {
  $jsonSchema: {
    bsonType: 'object',
    required: ['user_id', 'product_id', 'event_type', 'timestamp'],
    properties: {
      user_id: {bsonType: ['int', 'long'], minimum: 0},
      product_id: {bsonType: ['int', 'long'], minimum: 1},
      event_type: {bsonType: 'string', enum: ['view']},
      timestamp: {bsonType: 'date'}
    }
  }
});

ensureCollection('ProductSpecifications', {
  $jsonSchema: {
    bsonType: 'object',
    required: ['product_id', 'attributes', 'updated_at'],
    properties: {
      product_id: {bsonType: ['int', 'long'], minimum: 1},
      attributes: {bsonType: 'object'},
      updated_at: {bsonType: 'date'}
    }
  }
});

ensureCollection('OlistOrderReviews', {
  $jsonSchema: {
    bsonType: 'object',
    required: ['review_id', 'order_id', 'review_score', 'source'],
    properties: {
      review_id: {bsonType: 'string'},
      order_id: {bsonType: 'string'},
      review_score: {bsonType: ['int', 'long'], minimum: 1, maximum: 5},
      review_comment_title: {bsonType: 'string'},
      review_comment_message: {bsonType: 'string'},
      review_creation_date: {bsonType: 'string'},
      review_answer_timestamp: {bsonType: 'string'},
      source: {bsonType: 'string', enum: ['Olist']}
    }
  }
});

db.Reviews.createIndex(
  {product_id: 1, user_id: 1},
  {unique: true, name: 'unique_product_user_review'}
);
db.BrowsingHistory.createIndex(
  {user_id: 1, timestamp: -1},
  {name: 'history_by_user_time'}
);
db.BrowsingHistory.createIndex(
  {product_id: 1, event_type: 1},
  {name: 'history_by_product_type'}
);
db.ProductSpecifications.createIndex(
  {product_id: 1},
  {unique: true, name: 'unique_product_specifications'}
);
db.OlistOrderReviews.createIndex(
  {review_id: 1},
  {unique: true, name: 'unique_olist_review'}
);
