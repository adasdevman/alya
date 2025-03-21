from ..base import BaseIntegration
import requests
from typing import Dict, Any, List
import logging
from datetime import datetime, timedelta
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from quickbooks import QuickBooks
from quickbooks.objects.account import Account
from quickbooks.objects.bill import Bill
from quickbooks.objects.invoice import Invoice

logger = logging.getLogger(__name__)

class QuickBooksHandler(BaseIntegration):
    AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
    TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"
    
    def __init__(self, config):
        self.config = config
        self.validate_config(self.config)
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.redirect_uri = config['redirect_uri']
        self.access_token = config.get('access_token')
        self.realm_id = config.get('realm_id')  # Company ID
        self.initialize_client()

    def initialize_client(self):
        """Initialise le client QuickBooks"""
        self.auth_client = AuthClient(
            client_id=self.client_id,
            client_secret=self.client_secret,
            redirect_uri=self.redirect_uri,
            environment='production'
        )
        
        self.client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=self.config.get('refresh_token'),
            company_id=self.realm_id
        )

    def get_financial_summary(self, period: str = 'month') -> Dict[str, Any]:
        """Récupère un résumé des finances pour une période donnée"""
        try:
            # Définir la période
            today = datetime.now()
            if period == 'month':
                start_date = today.replace(day=1)
            elif period == 'quarter':
                start_date = today.replace(day=1, month=((today.month-1)//3)*3+1)
            elif period == 'year':
                start_date = today.replace(day=1, month=1)
            else:
                raise ValueError("Période non valide")

            # Récupérer les revenus
            invoices = Invoice.filter(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=today.strftime('%Y-%m-%d'),
                qb=self.client
            )
            
            total_revenue = sum(invoice.TotalAmt for invoice in invoices)

            # Récupérer les dépenses
            bills = Bill.filter(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=today.strftime('%Y-%m-%d'),
                qb=self.client
            )
            
            total_expenses = sum(bill.TotalAmt for bill in bills)

            # Calculer les métriques
            return {
                'period': period,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': today.strftime('%Y-%m-%d'),
                'revenue': total_revenue,
                'expenses': total_expenses,
                'profit': total_revenue - total_expenses
            }

        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé financier: {str(e)}")
            raise

    def get_expense_categories(self) -> List[Dict[str, Any]]:
        """Récupère les dépenses par catégorie"""
        try:
            # Récupérer toutes les dépenses du mois en cours
            start_date = datetime.now().replace(day=1)
            end_date = datetime.now()

            bills = Bill.filter(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                qb=self.client
            )

            # Organiser les dépenses par catégorie
            categories = {}
            for bill in bills:
                for line in bill.Line:
                    account = Account.get(line.AccountBasedExpenseLineDetail.AccountRef.value, qb=self.client)
                    category = account.Name
                    amount = line.Amount
                    
                    if category in categories:
                        categories[category] += amount
                    else:
                        categories[category] = amount

            # Convertir en liste pour le retour
            return [
                {'category': cat, 'amount': amount}
                for cat, amount in sorted(
                    categories.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            ]

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des catégories de dépenses: {str(e)}")
            raise

    def get_cash_flow(self, days: int = 30) -> Dict[str, Any]:
        """Analyse le flux de trésorerie sur une période donnée"""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Récupérer les entrées d'argent (factures payées)
            paid_invoices = Invoice.filter(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                qb=self.client
            )
            
            inflow = sum(invoice.TotalAmt for invoice in paid_invoices if invoice.Balance == 0)

            # Récupérer les sorties d'argent (factures payées)
            paid_bills = Bill.filter(
                start_date=start_date.strftime('%Y-%m-%d'),
                end_date=end_date.strftime('%Y-%m-%d'),
                qb=self.client
            )
            
            outflow = sum(bill.TotalAmt for bill in paid_bills if bill.Balance == 0)

            return {
                'period_days': days,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d'),
                'cash_inflow': inflow,
                'cash_outflow': outflow,
                'net_cash_flow': inflow - outflow
            }

        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du flux de trésorerie: {str(e)}")
            raise

    def get_accounts_receivable(self) -> List[Dict[str, Any]]:
        """Récupère les factures impayées"""
        try:
            invoices = Invoice.filter(
                Balance_GreaterThan=0,
                qb=self.client
            )

            return [{
                'invoice_id': invoice.Id,
                'customer': invoice.CustomerRef.name,
                'amount': invoice.TotalAmt,
                'balance': invoice.Balance,
                'due_date': invoice.DueDate,
                'days_overdue': (datetime.now() - datetime.strptime(invoice.DueDate, '%Y-%m-%d')).days
                if invoice.DueDate and datetime.strptime(invoice.DueDate, '%Y-%m-%d') < datetime.now()
                else 0
            } for invoice in invoices]

        except Exception as e:
            logger.error(f"Erreur lors de la récupération des comptes clients: {str(e)}")
            raise 