from django.contrib.contenttypes.models import ContentType

from nautobot.apps.jobs import Job, StringVar, IntegerVar, ObjectVar, register_jobs
from nautobot.dcim.models import Location, LocationType, Device, Manufacturer, DeviceType
from nautobot.extras.models import Status, Role


class NewBranch(Job):
    class Meta:
        name = "New Branch"
        description = "Provision a new branch location"
        field_order = ["location_name", "switch_count", "switch_model"]

    location_name = StringVar(description="Name of the new location")
    switch_count = IntegerVar(description="Number of access switches to create")
    manufacturer = ObjectVar(model=Manufacturer, required=False)
    switch_model = ObjectVar(
        description="Access switch model", model=DeviceType, query_params={"manufacturer_id": "$manufacturer"}
    )

    def run(self, location_name, switch_count, switch_model):
        STATUS_PLANNED = Status.objects.get(name="Planned")

        # Create the new location
        root_type = LocationType.objects.get_or_create(name="Campus")
        location = Location(
            name=location_name,
            location_type=root_type,
            status=STATUS_PLANNED,
        )
        location.validated_save()
        self.logger.info("Created new location", extra={"object": location})

        # Create access switches
        device_ct = ContentType.objects.get_for_model(Device)
        switch_role = Role.objects.get(name="Access Switch")
        switch_role.content_types.add(device_ct)
        for i in range(1, switch_count + 1):
            switch = Device(
                device_type=switch_model,
                name=f"{location.name}-switch{i}",
                location=location,
                status=STATUS_PLANNED,
                role=switch_role,
            )
            switch.validated_save()
            self.logger.info("Created new switch", extra={"object": switch})

        # Generate a CSV table of new devices
        output = ["name,make,model"]
        for switch in Device.objects.filter(location=location):
            attrs = [switch.name, switch.device_type.manufacturer.name, switch.device_type.model]
            output.append(",".join(attrs))

        return "\n".join(output)


register_jobs(NewBranch)
