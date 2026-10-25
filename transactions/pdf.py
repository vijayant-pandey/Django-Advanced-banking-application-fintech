from reportlab.pdfgen import canvas

def generate_statement_pdf(transactions, account_number):
    file_name = f"statement_{account_number}.pdf"
    c = canvas.Canvas(file_name)

    y = 800
    c.drawString(50, y, f"Account Statement: {account_number}")
    y -= 40

    for txn in transactions:
        c.drawString(
            50, y,
            f"{txn.created_at} | {txn.transaction_type} | {txn.amount} | {txn.balance_after_transaction}"
        )
        y -= 20

        if y < 50:
            c.showPage()
            y = 800

    c.save()
    return file_name
