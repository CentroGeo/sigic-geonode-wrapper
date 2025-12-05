from django.db import migrations, models


CONSTRAINT_NAME = "service_owner_base_url_unique"


def _alter_base_url_unique(apps, schema_editor, unique):
    Service = apps.get_model("services", "Service")
    old_field = Service._meta.get_field("base_url")
    new_field = models.URLField(db_index=True, unique=unique)
    new_field.set_attributes_from_name("base_url")
    schema_editor.alter_field(Service, old_field, new_field, preserve_default=True)


def _add_owner_scoped_constraint(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    constraint = models.UniqueConstraint(
        fields=["owner", "base_url"],
        name=CONSTRAINT_NAME,
    )
    schema_editor.add_constraint(Service, constraint)


def _remove_owner_scoped_constraint(apps, schema_editor):
    Service = apps.get_model("services", "Service")
    constraint = models.UniqueConstraint(
        fields=["owner", "base_url"],
        name=CONSTRAINT_NAME,
    )
    schema_editor.remove_constraint(Service, constraint)


def forwards(apps, schema_editor):
    _alter_base_url_unique(apps, schema_editor, unique=False)
    _add_owner_scoped_constraint(apps, schema_editor)


def backwards(apps, schema_editor):
    _remove_owner_scoped_constraint(apps, schema_editor)
    _alter_base_url_unique(apps, schema_editor, unique=True)


class Migration(migrations.Migration):
    dependencies = [
        ("services", "0054_alter_service_type"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]