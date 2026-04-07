import logging

logger = logging.getLogger(__name__)


class TransactionCleaner:
    """
    Removes unnecessary fields from transactions to reduce JSON size
    and keep only relevant data.
    
    Removes at transaction level:
    - Filing Date_link
    - Company Name_link  
    - 1d, 1w, 1m, 6m (empty performance fields)
    
    Keeps only essential fields in sec_filing_data.table_rows:
    - Field 3 (Code): Transaction Code
    - Field 3 (V): Transaction Code V flag
    - Field 6: Ownership Form
    - Field 7: Nature of Indirect Ownership
    """
    
    # Fields to keep in table_rows (in order)
    KEEP_FIELDS = [
        "3. Transaction Code (Instr. \n      8) | Code",
        "3. Transaction Code (Instr. \n      8) | V",
        "6. Ownership Form: Direct (D) or Indirect (I) (Instr. \n      4)",
        "7. Nature of Indirect Beneficial Ownership (Instr. \n      4)"
    ]
    
    # Transaction-level fields to remove
    REMOVE_TRANSACTION_FIELDS = {
        "Filing Date_link",
        "Company Name_link",
        "1d",
        "1w", 
        "1m",
        "6m"
    }
    
    def clean(self, result: dict) -> dict:
        """
        Remove unnecessary fields from transactions.
        
        Args:
            result: Pipeline output dict with 'transactions' list
            
        Returns:
            Updated result dict with cleaned transactions
        """
        transactions = result.get("transactions", [])
        
        for tx in transactions:
            # Remove transaction-level fields
            for field in self.REMOVE_TRANSACTION_FIELDS:
                tx.pop(field, None)
            
            # Clean SEC filing data table_rows
            sec_data = tx.get("sec_filing_data", {})
            table_rows = sec_data.get("table_rows", [])
            
            cleaned_rows = []
            for row in table_rows:
                # Preserve field order by iterating through KEEP_FIELDS list
                cleaned_row = {}
                for field in self.KEEP_FIELDS:
                    if field in row:
                        cleaned_row[field] = row[field]
                cleaned_rows.append(cleaned_row)
            
            if table_rows:
                sec_data["table_rows"] = cleaned_rows
        
        logger.info("Cleaned %d transactions - removed unnecessary fields", len(transactions))
        return result
