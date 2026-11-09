"""Small service-independent verification command for demonstrations."""
from shopsphere.document_store import DocumentStore
from shopsphere.sql_store import SQLStore


def main() -> None:
    store = SQLStore()
    user = store.authenticate("customer@shopsphere.local", "Customer123!")
    documents = DocumentStore()
    assert user and store.catalogue()
    documents.record_view(user["user_id"], store.catalogue()[0]["product_id"])
    print("SQL authentication/catalogue: OK")
    print("Document browsing event: OK")


if __name__ == "__main__":
    main()
