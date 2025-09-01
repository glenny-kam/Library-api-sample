from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)

# In-memory database (in production, use a real database)
books = [
    {
        "id": "b001",
        "title": "The Great Gatsby",
        "author": "F. Scott Fitzgerald",
        "isbn": "978-0-7432-7356-5",
        "category": "Fiction",
        "publication_year": 1925,
        "available_copies": 3,
        "total_copies": 5,
        "location": "Section A, Shelf 1"
    },
    {
        "id": "b002",
        "title": "To Kill a Mockingbird",
        "author": "Harper Lee",
        "isbn": "978-0-06-112008-4",
        "category": "Fiction",
        "publication_year": 1960,
        "available_copies": 2,
        "total_copies": 4,
        "location": "Section A, Shelf 2"
    },
    {
        "id": "b003",
        "title": "Data Science from Scratch",
        "author": "Joel Grus",
        "isbn": "978-1-492-04113-9",
        "category": "Technology",
        "publication_year": 2019,
        "available_copies": 1,
        "total_copies": 2,
        "location": "Section C, Shelf 5"
    }
]

members = [
    {
        "id": "m001",
        "name": "John Doe",
        "email": "john.doe@email.com",
        "phone": "+1234567890",
        "membership_date": "2024-01-15",
        "membership_type": "Premium",
        "status": "Active"
    },
    {
        "id": "m002",
        "name": "Jane Smith",
        "email": "jane.smith@email.com",
        "phone": "+1987654321",
        "membership_date": "2024-02-20",
        "membership_type": "Standard",
        "status": "Active"
    }
]

borrowed_books = [
    {
        "id": "br001",
        "book_id": "b001",
        "member_id": "m001",
        "borrow_date": "2024-08-20",
        "due_date": "2024-09-03",
        "return_date": None,
        "status": "Borrowed",
        "fine_amount": 0.0
    },
    {
        "id": "br002",
        "book_id": "b002",
        "member_id": "m002",
        "borrow_date": "2024-08-15",
        "due_date": "2024-08-29",
        "return_date": "2024-08-28",
        "status": "Returned",
        "fine_amount": 0.0
    }
]


# Utility functions

def generate_id(prefix):
    return f"{prefix}{str(uuid.uuid4())[:8]}"


def find_item_by_id(items, item_id):
    return next((item for item in items if item["id"] == item_id), None)


def calculate_fine(due_date_str, return_date_str=None):
    due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
    return_date = (
        datetime.strptime(return_date_str, "%Y-%m-%d")
        if return_date_str else datetime.now()
    )
    if return_date > due_date:
        days_overdue = (return_date - due_date).days
        return days_overdue * 2.0  # $2 per day fine
    return 0.0


# ==================== BOOK ENDPOINTS ====================

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Welcome to the Library Management API!",
        "version": "1.0",
        "endpoints": {
            "books": "/api/books",
            "members": "/api/members",
            "borrowing": "/api/borrow",
            "returns": "/api/return"
        }
    })


@app.route("/api/books", methods=["GET"])
def get_books():
    # Optional query parameters for filtering
    category = request.args.get('category')
    author = request.args.get('author')
    available_only = request.args.get('available', 'false').lower() == 'true'
    filtered_books = books
    if category:
        filtered_books = [
            b for b in filtered_books
            if b['category'].lower() == category.lower()
        ]
    if author:
        filtered_books = [
            b for b in filtered_books
            if author.lower() in b['author'].lower()
            ]
    if available_only:
        filtered_books = [b for b in filtered_books if b['available_copies']
                          > 0]
    return jsonify({
        "books": filtered_books,
        "total": len(filtered_books)
    })


@app.route("/api/books/<book_id>", methods=["GET"])
def get_book(book_id):
    book = find_item_by_id(books, book_id)
    if book:
        return jsonify(book)
    return jsonify({"error": "Book not found"}), 404


@app.route("/api/books", methods=["POST"])
def add_book():
    try:
        data = request.get_json()
        # Validate required fields
        required_fields = ["title", "author", "isbn", "category",
                           "total_copies"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"
                                }), 400
        new_book = {
            "id": generate_id("b"),
            "title": data["title"],
            "author": data["author"],
            "isbn": data["isbn"],
            "category": data["category"],
            "publication_year": data.get("publication_year",
                                         datetime.now().year),
            "total_copies": data["total_copies"],
            "available_copies": data["total_copies"],
            # Initially all available
            "location": data.get("location", "Not assigned")
        }
        books.append(new_book)
        return jsonify(new_book), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/books/<book_id>", methods=["PUT"])
def update_book(book_id):
    book = find_item_by_id(books, book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    try:
        data = request.get_json()
        # Update allowed fields
        updatable_fields = ["title", "author", "category", "publication_year",
                            "total_copies", "location"]
        for field in updatable_fields:
            if field in data:
                book[field] = data[field]
        # Recalculate available copies if total_copies changed
        if "total_copies" in data:
            borrowed_count = len([
                b for b in borrowed_books if b["book_id"] == book_id and
                b["status"] == "Borrowed"])
            book["available_copies"] = book["total_copies"] - borrowed_count
        return jsonify(book)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/books/<book_id>", methods=["DELETE"])
def delete_book(book_id):
    book = find_item_by_id(books, book_id)
    if not book:
        return jsonify({"error": "Book not found"}), 404
    # Check if book is currently borrowed
    active_borrows = [
        b for b in borrowed_books if b["book_id"] == book_id and
        b["status"] == "Borrowed"]
    if active_borrows:
        return jsonify({
            "error": "Cannot delete book that is currently borrowed"}), 400
    books.remove(book)
    return jsonify({"message": "Book deleted successfully"})


# ==================== MEMBER ENDPOINTS ====================

@app.route("/api/members", methods=["GET"])
def get_members():
    return jsonify({
        "members": members,
        "total": len(members)
    })


@app.route("/api/members/<member_id>", methods=["GET"])
def get_member(member_id):
    member = find_item_by_id(members, member_id)
    if member:
        # Include borrowing history
        member_borrows = [
            b for b in borrowed_books if b["member_id"] == member_id]
        member_info = member.copy()
        member_info["borrowing_history"] = member_borrows
        return jsonify(member_info)
    return jsonify({"error": "Member not found"}), 404


@app.route("/api/members", methods=["POST"])
def add_member():
    try:
        data = request.get_json()
        required_fields = ["name", "email", "phone"]
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"
                                }), 400
        new_member = {
            "id": generate_id("m"),
            "name": data["name"],
            "email": data["email"],
            "phone": data["phone"],
            "membership_date": datetime.now().strftime("%Y-%m-%d"),
            "membership_type": data.get("membership_type", "Standard"),
            "status": "Active"
        }
        members.append(new_member)
        return jsonify(new_member), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# ==================== BORROWING ENDPOINTS ====================


@app.route("/api/borrow", methods=["POST"])
def borrow_book():
    try:
        data = request.get_json()
        book_id = data.get("book_id")
        member_id = data.get("member_id")
        if not book_id or not member_id:
            return jsonify({"error": "book_id and member_id are required"
                            }), 400
        # Validate book exists and is available
        book = find_item_by_id(books, book_id)
        if not book:
            return jsonify({"error": "Book not found"}), 404
        if book["available_copies"] <= 0:
            return jsonify({"error": "Book not available"}), 400
        # Validate member exists
        member = find_item_by_id(members, member_id)
        if not member:
            return jsonify({"error": "Member not found"}), 404
        if member["status"] != "Active":
            return jsonify({"error": "Member account is not active"}), 400
        # Check if member already has this book
        active_borrow = next(
            (
                b for b in borrowed_books
                if (
                    b["book_id"] == book_id
                    and b["member_id"] == member_id
                    and b["status"] == "Borrowed"
                )
            ),
            None
        )
        if active_borrow:
            return jsonify({"error": "Member already has this book borrowed"
                            }), 400
        # Create borrow record
        borrow_date = datetime.now()
        due_date = borrow_date + timedelta(days=14)  # 2 weeks borrowing period
        new_borrow = {
            "id": generate_id("br"),
            "book_id": book_id,
            "member_id": member_id,
            "borrow_date": borrow_date.strftime("%Y-%m-%d"),
            "due_date": due_date.strftime("%Y-%m-%d"),
            "return_date": None,
            "status": "Borrowed",
            "fine_amount": 0.0
        }
        borrowed_books.append(new_borrow)
        # Update book availability
        book["available_copies"] -= 1
        return jsonify({
            "message": "Book borrowed successfully",
            "borrow_record": new_borrow,
            "book_title": book["title"],
            "member_name": member["name"]
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/return", methods=["POST"])
def return_book():
    try:
        data = request.get_json()
        book_id = data.get("book_id")
        member_id = data.get("member_id")
        if not book_id or not member_id:
            return jsonify({"error": "book_id and member_id are required"
                            }), 400
        # Find active borrow record
        borrow_record = next(
            (b for b in borrowed_books if (
                    b["book_id"] == book_id
                    and b["member_id"] == member_id
                    and b["status"] == "Borrowed"
                )
             ),
            None
        )
        if not borrow_record:
            return jsonify({"error": "No active borrow record found"
                            }), 404
        # Calculate fine if overdue
        return_date = datetime.now().strftime("%Y-%m-%d")
        fine = calculate_fine(borrow_record["due_date"], return_date)
        # Update borrow record
        borrow_record["return_date"] = return_date
        borrow_record["status"] = "Returned"
        borrow_record["fine_amount"] = fine
        # Update book availability
        book = find_item_by_id(books, book_id)
        book["available_copies"] += 1
        response_data = {
            "message": "Book returned successfully",
            "return_date": return_date,
            "fine_amount": fine,
            "book_title": book["title"]
        }
        if fine > 0:
            response_data["warning"] = (
                f"Book was overdue. Fine: ${fine:.2f}"
            )
        return jsonify(response_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    # ==================== REPORTING ENDPOINTS ====================


@app.route("/api/reports/overdue", methods=["GET"])
def get_overdue_books():
    today = datetime.now().strftime("%Y-%m-%d")
    overdue_books = []
    for borrow in borrowed_books:
        if borrow["status"] == "Borrowed" and borrow["due_date"] < today:
            book = find_item_by_id(books, borrow["book_id"])
            member = find_item_by_id(members, borrow["member_id"])
            due_date_dt = datetime.strptime(borrow["due_date"], "%Y-%m-%d")
            days_overdue = (datetime.now() - due_date_dt).days
            fine = days_overdue * 2.0
            overdue_books.append({
                "borrow_id": borrow["id"],
                "book_title": book["title"],
                "member_name": member["name"],
                "member_email": member["email"],
                "due_date": borrow["due_date"],
                "days_overdue": days_overdue,
                "fine_amount": fine
            })
    return jsonify({
        "overdue_books": overdue_books,
        "total_overdue": len(overdue_books)
    })


@app.route("/api/reports/popular-books", methods=["GET"])
def get_popular_books():
    # Count how many times each book has been borrowed
    book_borrow_count = {}
    for borrow in borrowed_books:
        book_id = borrow["book_id"]
        book_borrow_count[book_id] = book_borrow_count.get(book_id, 0) + 1
    # Create report with book details
    popular_books = []
    sorted_books = sorted(
        book_borrow_count.items(),
        key=lambda x: x[1],
        reverse=True
    )
    for book_id, count in sorted_books:
        book = find_item_by_id(books, book_id)
        popular_books.append({
            "book_id": book_id,
            "title": book["title"],
            "author": book["author"],
            "times_borrowed": count
        })
    return jsonify({
        "popular_books": popular_books,
        "total_books_analyzed": len(popular_books)
        })


@app.route("/api/reports/member-activity/<member_id>", methods=["GET"])
def get_member_activity(member_id):
    member = find_item_by_id(members, member_id)
    if not member:
        return jsonify({"error": "Member not found"}), 404
    member_borrows = [b for b in borrowed_books if b["member_id"] == member_id]
    # Calculate statistics
    total_books_borrowed = len(member_borrows)
    books_currently_borrowed = len([
        b for b in member_borrows
        if b["status"] == "Borrowed"
    ])
    total_fines = sum(b["fine_amount"] for b in member_borrows)
    return jsonify({
            "member": member,
            "activity": {
                "total_books_borrowed": total_books_borrowed,
                "books_currently_borrowed": books_currently_borrowed,
                "total_fines_paid": total_fines,
                "borrowing_history": member_borrows
            }
        })
    # ==================== SEARCH ENDPOINTS ====================


@app.route("/api/search", methods=["GET"])
def search_books():
    query = request.args.get('q', '').lower()
    search_type = request.args.get('type', 'all')  # all, title, author, isbn
    if not query:
        return jsonify({"error": "Search query 'q' is required"}), 400
    results = []
    for book in books:
        match = False
        if search_type == 'all':
            match = (
                query in book['title'].lower() or
                query in book['author'].lower() or
                query in book['isbn'].lower() or
                query in book['category'].lower()
            )
        elif search_type == 'title':
            match = query in book['title'].lower()
        elif search_type == 'author':
            match = query in book['author'].lower()
        elif search_type == 'isbn':
            match = query in book['isbn'].lower()
        if match:
            results.append(book)
    return jsonify({
        "query": query,
        "search_type": search_type,
        "results": results,
        "total_found": len(results)
    })
    # ==================== STATISTICS ENDPOINT ====================
    # ==================== STATISTICS ENDPOINT ====================


@app.route("/api/stats", methods=["GET"])
def get_library_stats():
    total_books = len(books)
    total_copies = sum(book["total_copies"] for book in books)
    available_copies = sum(book["available_copies"] for book in books)
    borrowed_copies = total_copies - available_copies
    total_members = len(members)
    active_members = len([m for m in members if m["status"] == "Active"])
    total_borrows = len(borrowed_books)
    active_borrows = len([
        b for b in borrowed_books
        if b["status"] == "Borrowed"
    ])
    # Category distribution
    categories = {}
    for book in books:
        category = book["category"]
        categories[category] = categories.get(category, 0) + 1

    return jsonify({
        "library_statistics": {
            "books": {
                "total_unique_books": total_books,
                "total_copies": total_copies,
                "available_copies": available_copies,
                "borrowed_copies": borrowed_copies,
                "utilization_rate": (
                    f"{(borrowed_copies/total_copies)*100:.1f}%"
                )
            },
            "members": {
                "total_members": total_members,
                "active_members": active_members
            },
            "borrowing": {
                "total_borrowing_records": total_borrows,
                "currently_borrowed": active_borrows
            },
            "categories": categories
        }
    })

# ==================== ERROR HANDLERS ====================


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(400)
def bad_request(error):
    return jsonify({"error": "Bad request"}), 400


# ==================== MAIN ====================

if __name__ == "__main__":
    print("🚀 Starting Library Management API...")
    print("📚 Available endpoints:")
    print("  GET  /                     - API Info")
    print("  GET  /api/books           - Get all books")
    print("  POST /api/books           - Add new book")
    print("  GET  /api/books/<id>      - Get book by ID")
    print("  PUT  /api/books/<id>      - Update book")
    print("  GET  /api/members         - Get all members")
    print("  POST /api/members         - Add new member")
    print("  POST /api/borrow          - Borrow a book")
    print("  POST /api/return          - Return a book")
    print("  GET  /api/search?q=query  - Search books")
    print("  GET  /api/reports/overdue - Get overdue books")
    print("  GET  /api/stats           - Library statistics")
    print("\n🌐 Server running at: http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
