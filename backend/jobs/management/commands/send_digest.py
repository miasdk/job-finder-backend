from django.core.management.base import BaseCommand
from jobs.email_digest import EmailDigestManager

class Command(BaseCommand):
    help = 'Send daily job digest email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force send digest even if there are few jobs'
        )
        parser.add_argument(
            '--min-score',
            type=float,
            default=70,
            help='Minimum score for top matches'
        )

    def handle(self, *args, **options):
        digest_manager = EmailDigestManager()
        
        if options.get('force'):
            # Override the should_send_digest method temporarily
            original_method = digest_manager.should_send_digest
            digest_manager.should_send_digest = lambda jobs_data: True
        
        self.stdout.write("Preparing to send daily job digest...")
        
        try:
            success = digest_manager.send_digest()
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS("Successfully sent email digest!")
                )
            else:
                self.stdout.write(
                    self.style.WARNING("Email digest was not sent (not enough quality jobs)")
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error sending digest: {str(e)}")
            )