from django.core.management.base import BaseCommand
from main.models import Building, PickupPoint

class Command(BaseCommand):
    help = 'Создает и обновляет пункты выдачи'

    def handle(self, *args, **options):
        points_data = {
            'ГУК': {
                'latitude': 56.844033,
                'longitude': 60.654077,
                'address': 'ул. Мира, 19, Екатеринбург'
            },
            'ФТИ': {
                'latitude': 56.842059,
                'longitude': 60.651921,
                'address': 'ул. Мира, 21, Екатеринбург'
            },
            'ИНМТ': {
                'latitude': 56.842157,
                'longitude': 60.649092,
                'address': 'ул. Мира, 28, Екатеринбург'
            },
            'ИРИТ-РТФ': {
                'latitude': 56.840823,
                'longitude': 60.650763,
                'address': 'ул. Мира, 32, Екатеринбург'
            },
            'УГИ': {
                'latitude': 56.840429,
                'longitude': 60.616204,
                'address': 'ул. Ленина, 51, Екатеринбург'
            },
        }

        for name, data in points_data.items():
            try:
                building = Building.objects.get(name=name)

                point, created = PickupPoint.objects.update_or_create(
                    name=name,
                    defaults={
                        'building': building,
                        'latitude': data['latitude'],
                        'longitude': data['longitude'],
                        'address': data['address'],
                    }
                )

                if created:
                    self.stdout.write(
                        self.style.SUCCESS(f'Создан пункт: {name}')
                    )
                else:
                    self.stdout.write(
                        self.style.SUCCESS(f'Обновлён пункт: {name}')
                    )

            except Building.DoesNotExist:
                self.stdout.write(
                    self.style.WARNING(
                        f'Корпус "{name}" не найден в таблице Building'
                    )
                )