import logging
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from quickbooks import QuickBooks
from quickbooks.objects.account import Account
from quickbooks.objects.bill import Bill
from quickbooks.objects.invoice import Invoice
from datetime import datetime

logger = logging.getLogger(__name__)

class QuickBooksManager:
    @classmethod
    def get_financial_summary(cls, user_integration, start_date=None, end_date=None):
        """Récupère un résumé financier"""
        try:
            auth_client = AuthClient(
                client_id=user_integration.config.get('client_id'),
                client_secret=user_integration.config.get('client_secret'),
                access_token=user_integration.access_token,
                refresh_token=user_integration.refresh_token,
                environment='sandbox'  # ou 'production'
            )
            
            client = QuickBooks(
                auth_client=auth_client,
                refresh_token=user_integration.refresh_token,
                company_id=user_integration.config.get('realm_id')
            )
            
            # Récupérer les revenus
            income = cls._get_income(client, start_date, end_date)
            
            # Récupérer les dépenses
            expenses = cls._get_expenses(client, start_date, end_date)
            
            # Calculer les totaux
            total_income = sum(income.values())
            total_expenses = sum(expenses.values())
            
            return {
                'income': income,
                'expenses': expenses,
                'total_income': total_income,
                'total_expenses': total_expenses,
                'net_profit': total_income - total_expenses
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération résumé QuickBooks: {str(e)}")
            raise

    @classmethod
    def _get_income(cls, client, start_date=None, end_date=None):
        """Récupère les revenus par catégorie"""
        income = {}
        
        # Récupérer les factures
        invoices = Invoice.filter(
            start_date=start_date,
            end_date=end_date,
            qb=client
        )
        
        for invoice in invoices:
            if invoice.TotalAmt:
                category = invoice.CustomerRef.name if invoice.CustomerRef else 'Autre'
                income[category] = income.get(category, 0) + float(invoice.TotalAmt)
                
        return income

    @classmethod
    def _get_expenses(cls, client, start_date=None, end_date=None):
        """Récupère les dépenses par catégorie"""
        expenses = {}
        
        # Récupérer les factures fournisseurs
        bills = Bill.filter(
            start_date=start_date,
            end_date=end_date,
            qb=client
        )
        
        for bill in bills:
            if bill.TotalAmt:
                category = bill.VendorRef.name if bill.VendorRef else 'Autre'
                expenses[category] = expenses.get(category, 0) + float(bill.TotalAmt)
                
        return expenses

    @classmethod
    def get_expense_details(cls, user_integration, category=None):
        """Récupère les détails des dépenses"""
        try:
            auth_client = AuthClient(
                client_id=user_integration.config.get('client_id'),
                client_secret=user_integration.config.get('client_secret'),
                access_token=user_integration.access_token,
                refresh_token=user_integration.refresh_token,
                environment='sandbox'  # ou 'production'
            )
            
            client = QuickBooks(
                auth_client=auth_client,
                refresh_token=user_integration.refresh_token,
                company_id=user_integration.config.get('realm_id')
            )
            
            query = Bill.filter(qb=client)
            if category:
                query = query.filter(VendorRef={'name': category})
                
            bills = query.all()
            
            return [{
                'date': bill.TxnDate,
                'vendor': bill.VendorRef.name if bill.VendorRef else 'Inconnu',
                'amount': float(bill.TotalAmt),
                'memo': bill.PrivateNote
            } for bill in bills]
            
        except Exception as e:
            logger.error(f"Erreur récupération dépenses QuickBooks: {str(e)}")
            raise 