# ShopSphere report draft

## 1. Introduction
ShopSphere is a multi-seller marketplace demonstrating normalized relational
transactions alongside document-oriented reviews, specifications and browsing
events.

## 2. Architecture and requirements
Streamlit provides the interface. MariaDB/SQLite owns durable transactional
records; MongoDB owns flexible operational documents. Role checks and
parameterized SQL protect customer, seller and administrator actions.

## 3. Database implementation
The relational model contains nine required entities and uses foreign keys,
indexes, views, aggregate queries and guarded inventory updates. MongoDB uses
three collections with product/user indexes and rating/browsing pipelines.

## 4. Discussion
Normalization supports integrity and checkout consistency. Documents support
schema flexibility and event aggregation. Cross-database writes are not
distributed transactions, which is an explicit reliability limitation.

## 5. Reflection
The project demonstrates why workload, consistency requirements and schema
change frequency should guide database selection.

## 6. References and appendix
Add the official module brief, Olist dataset citation, measured benchmark CSV,
screenshots and final ERD export before submission. Keep the final report
within the supplied template's ten-page body limit.
