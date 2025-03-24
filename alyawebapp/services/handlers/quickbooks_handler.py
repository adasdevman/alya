import logging
import json
import re
from datetime import datetime, timedelta
from ..exceptions import NetworkError, AITimeoutError

logger = logging.getLogger(__name__)

class QuickBooksHandler:
    """Gestionnaire pour les intégrations QuickBooks"""
    
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.user = orchestrator.user
        self.openai_client = orchestrator.openai_client
        self.conversation_state = None
        self.finance_info = {}
        self.quickbooks_integration = None
        self._initialize()
    
    def _initialize(self):
        """Initialise l'intégration QuickBooks si elle existe"""
        from alyawebapp.models import Integration, UserIntegration
        
        try:
            integration = Integration.objects.get(name__iexact='quickbooks')
            self.quickbooks_integration = UserIntegration.objects.get(
                user=self.user,
                integration=integration,
                enabled=True
            )
        except (Integration.DoesNotExist, UserIntegration.DoesNotExist):
            self.quickbooks_integration = None
    
    def handle_request(self, text):
        """Gère les requêtes liées à QuickBooks"""
        try:
            if not self.quickbooks_integration:
                return "Vous n'avez pas installé cette intégration."
            
            # Détecter les intentions de l'utilisateur
            text_lower = text.lower()
            
            # Intention d'obtenir un résumé financier
            if any(phrase in text_lower for phrase in ["résumé financier", "situation financière", "bilan financier"]):
                period_match = None
                if "mois" in text_lower:
                    period_match = "month"
                elif "trimestre" in text_lower:
                    period_match = "quarter"
                elif "année" in text_lower or "annuel" in text_lower:
                    period_match = "year"
                
                return self._get_financial_summary(period_match or "month")
            
            # Intention de voir les catégories de dépenses
            if any(phrase in text_lower for phrase in ["catégories de dépenses", "dépenses par catégorie", "répartition des dépenses"]):
                return self._get_expense_categories()
            
            # Intention d'analyser le flux de trésorerie
            if any(phrase in text_lower for phrase in ["flux de trésorerie", "cash flow", "liquidités"]):
                days_match = re.search(r'(\d+)\s*jours', text_lower)
                days = int(days_match.group(1)) if days_match else 30
                return self._get_cash_flow(days)
            
            # Intention de voir les factures impayées
            if any(phrase in text_lower for phrase in ["factures impayées", "comptes clients", "créances"]):
                return self._get_accounts_receivable()
            
            return "Je peux vous aider avec QuickBooks. Voici ce que je peux faire :\n" + \
                   "- Obtenir un résumé financier (mensuel, trimestriel ou annuel)\n" + \
                   "- Afficher les catégories de dépenses\n" + \
                   "- Analyser le flux de trésorerie\n" + \
                   "- Consulter les factures impayées"

        except Exception as e:
            logger.error(f"Erreur QuickBooks: {str(e)}")
            self.conversation_state = None  # Réinitialiser l'état en cas d'erreur
            return "Une erreur est survenue lors de l'exécution de votre demande. Veuillez réessayer."
    
    def _get_financial_summary(self, period):
        """Récupère un résumé financier en utilisant l'intégration QuickBooks existante"""
        from alyawebapp.integrations.quickbooks.handler import QuickBooksHandler as QuickBooksAPI
        
        try:
            # Utiliser l'implémentation existante
            qb_handler = QuickBooksAPI(self.quickbooks_integration.config)
            summary = qb_handler.get_financial_summary(period)
            
            # Formater le résumé pour l'affichage
            period_labels = {
                "month": "mensuel",
                "quarter": "trimestriel",
                "year": "annuel"
            }
            
            response = f"📊 Résumé financier {period_labels.get(period, 'mensuel')} ({summary['start_date']} à {summary['end_date']}) :\n\n"
            response += f"• Revenus : {summary['revenue']:.2f} €\n"
            response += f"• Dépenses : {summary['expenses']:.2f} €\n"
            response += f"• Bénéfice/Perte : {summary['profit']:.2f} €\n"
            
            if summary['profit'] > 0:
                response += "\n✅ Bilan positif pour cette période !"
            else:
                response += "\n⚠️ Bilan négatif pour cette période."
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du résumé financier: {str(e)}")
            return "Désolé, je n'ai pas pu récupérer le résumé financier. Veuillez vérifier que votre intégration QuickBooks est correctement configurée."
    
    def _get_expense_categories(self):
        """Récupère les catégories de dépenses en utilisant l'intégration QuickBooks existante"""
        from alyawebapp.integrations.quickbooks.handler import QuickBooksHandler as QuickBooksAPI
        
        try:
            # Utiliser l'implémentation existante
            qb_handler = QuickBooksAPI(self.quickbooks_integration.config)
            categories = qb_handler.get_expense_categories()
            
            if not categories:
                return "Aucune dépense enregistrée pour le mois en cours."
            
            # Calculer le total des dépenses
            total_expenses = sum(cat['amount'] for cat in categories)
            
            # Formater les catégories pour l'affichage
            response = "📊 Répartition des dépenses du mois :\n\n"
            for i, cat in enumerate(categories, 1):
                percentage = (cat['amount'] / total_expenses) * 100
                response += f"• {cat['category']} : {cat['amount']:.2f} € ({percentage:.1f}%)\n"
            
            response += f"\nTotal des dépenses : {total_expenses:.2f} €"
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des catégories de dépenses: {str(e)}")
            return "Désolé, je n'ai pas pu récupérer les catégories de dépenses. Veuillez vérifier que votre intégration QuickBooks est correctement configurée."
    
    def _get_cash_flow(self, days):
        """Analyse le flux de trésorerie en utilisant l'intégration QuickBooks existante"""
        from alyawebapp.integrations.quickbooks.handler import QuickBooksHandler as QuickBooksAPI
        
        try:
            # Utiliser l'implémentation existante
            qb_handler = QuickBooksAPI(self.quickbooks_integration.config)
            cash_flow = qb_handler.get_cash_flow(days)
            
            # Formater le flux de trésorerie pour l'affichage
            response = f"💰 Analyse du flux de trésorerie (derniers {days} jours) :\n\n"
            response += f"• Entrées : {cash_flow['cash_inflow']:.2f} €\n"
            response += f"• Sorties : {cash_flow['cash_outflow']:.2f} €\n"
            response += f"• Flux net : {cash_flow['net_cash_flow']:.2f} €\n\n"
            
            if cash_flow['net_cash_flow'] > 0:
                response += "✅ Votre flux de trésorerie est positif sur cette période."
            else:
                response += "⚠️ Votre flux de trésorerie est négatif sur cette période."
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse du flux de trésorerie: {str(e)}")
            return "Désolé, je n'ai pas pu analyser le flux de trésorerie. Veuillez vérifier que votre intégration QuickBooks est correctement configurée."
    
    def _get_accounts_receivable(self):
        """Récupère les factures impayées en utilisant l'intégration QuickBooks existante"""
        from alyawebapp.integrations.quickbooks.handler import QuickBooksHandler as QuickBooksAPI
        
        try:
            # Utiliser l'implémentation existante
            qb_handler = QuickBooksAPI(self.quickbooks_integration.config)
            receivables = qb_handler.get_accounts_receivable()
            
            if not receivables:
                return "Aucune facture impayée actuellement. ✅"
            
            # Calculer le total des créances
            total_receivable = sum(inv['balance'] for inv in receivables)
            overdue_receivable = sum(inv['balance'] for inv in receivables if inv['days_overdue'] > 0)
            
            # Formater les factures pour l'affichage
            response = "📑 Factures impayées :\n\n"
            
            # D'abord les factures en retard
            overdue = [inv for inv in receivables if inv['days_overdue'] > 0]
            if overdue:
                response += "⚠️ FACTURES EN RETARD :\n"
                for inv in overdue:
                    response += f"• {inv['customer']} : {inv['balance']:.2f} € (retard de {inv['days_overdue']} jours)\n"
                response += "\n"
            
            # Ensuite les factures à venir
            upcoming = [inv for inv in receivables if inv['days_overdue'] <= 0]
            if upcoming:
                response += "FACTURES À ÉCHÉANCE :\n"
                for inv in upcoming:
                    response += f"• {inv['customer']} : {inv['balance']:.2f} € (échéance : {inv['due_date']})\n"
            
            response += f"\nTotal à recevoir : {total_receivable:.2f} €"
            if overdue_receivable > 0:
                response += f" dont {overdue_receivable:.2f} € en retard"
            
            return response
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des factures impayées: {str(e)}")
            return "Désolé, je n'ai pas pu récupérer les factures impayées. Veuillez vérifier que votre intégration QuickBooks est correctement configurée." 