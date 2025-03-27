document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Initialize Bootstrap modal
    const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));

    // Calculate schedule positions and handle overlaps
    function positionSchedules() {
        const daySlots = document.querySelectorAll('.day-slots');
        daySlots.forEach(daySlot => {
            const events = daySlot.querySelectorAll('.schedule-event');
            const eventArray = Array.from(events);

            // Sort events by start time
            eventArray.sort((a, b) => {
                const aStart = new Date(a.dataset.startTime);
                const bStart = new Date(b.dataset.startTime);
                return aStart - bStart;
            });

            // Find overlapping groups
            const overlappingGroups = [];

            eventArray.forEach(event => {
                let foundGroup = false;
                const eventStart = new Date(event.dataset.startTime);
                const eventEnd = new Date(event.dataset.endTime);

                // Normalize end time - treat 00:00 as 24:00
                const normalizedEndHour = eventEnd.getHours() === 0 && eventEnd.getMinutes() === 0 
                    ? 24 
                    : eventEnd.getHours() + eventEnd.getMinutes() / 60;

                // Check if event overlaps with any existing group
                for (let group of overlappingGroups) {
                    const overlapsWithGroup = group.some(existingEvent => {
                        const existingStart = new Date(existingEvent.dataset.startTime);
                        const existingEnd = new Date(existingEvent.dataset.endTime);
                        const existingEndHour = existingEnd.getHours() === 0 && existingEnd.getMinutes() === 0 
                            ? 24 
                            : existingEnd.getHours() + existingEnd.getMinutes() / 60;

                        return (
                            eventStart < (existingEndHour === 24 ? new Date(existingEnd).setHours(24, 0, 0) : existingEnd) && 
                            (normalizedEndHour === 24 ? new Date(eventEnd).setHours(24, 0, 0) : eventEnd) > existingStart
                        );
                    });

                    if (overlapsWithGroup) {
                        group.push(event);
                        foundGroup = true;
                        break;
                    }
                }

                // If no overlapping group found, create new group
                if (!foundGroup) {
                    overlappingGroups.push([event]);
                }

                // Merge overlapping groups
                for (let i = overlappingGroups.length - 1; i > 0; i--) {
                    for (let j = i - 1; j >= 0; j--) {
                        const groupOverlaps = overlappingGroups[i].some(event1 => 
                            overlappingGroups[j].some(event2 => {
                                const start1 = new Date(event1.dataset.startTime);
                                const end1 = new Date(event1.dataset.endTime);
                                const end1Hour = end1.getHours() === 0 && end1.getMinutes() === 0 ? 24 : end1.getHours() + end1.getMinutes() / 60;

                                const start2 = new Date(event2.dataset.startTime);
                                const end2 = new Date(event2.dataset.endTime);
                                const end2Hour = end2.getHours() === 0 && end2.getMinutes() === 0 ? 24 : end2.getHours() + end2.getMinutes() / 60;

                                return (
                                    start1 < (end2Hour === 24 ? new Date(end2).setHours(24, 0, 0) : end2) && 
                                    (end1Hour === 24 ? new Date(end1).setHours(24, 0, 0) : end1) > start2
                                );
                            })
                        );

                        if (groupOverlaps) {
                            overlappingGroups[j] = [...overlappingGroups[j], ...overlappingGroups[i]];
                            overlappingGroups.splice(i, 1);
                            break;
                        }
                    }
                }
            });

            // Position events vertically and handle overlaps
            eventArray.forEach(event => {
                const startTime = new Date(event.dataset.startTime);
                const endTime = new Date(event.dataset.endTime);
                const startHour = startTime.getHours() + startTime.getMinutes() / 60;
                let endHour = endTime.getHours() + endTime.getMinutes() / 60;

                // Special handling for midnight (00:00) as end time
                if (endHour === 0) {
                    endHour = 24;
                }

                const top = startHour * 60;
                const height = (endHour - startHour) * 60;

                event.style.top = `${top}px`;
                event.style.height = `${height}px`;
            });

            // Position overlapping events horizontally
            overlappingGroups.forEach(group => {
                if (group.length > 1) {
                    const width = 100 / group.length;
                    group.forEach((event, index) => {
                        event.style.width = `calc(${width}% - 4px)`;
                        event.style.left = `calc(${index * width}% + 2px)`;
                        event.style.boxSizing = 'border-box';
                    });
                }
            });
        });
    }

    // Handle schedule event clicks
    document.querySelectorAll('.schedule-event').forEach(event => {
        event.addEventListener('click', function(e) {
            e.stopPropagation();
            const scheduleId = this.dataset.scheduleId;
            const startTime = new Date(this.dataset.startTime);
            const endTime = new Date(this.dataset.endTime);
            const description = this.querySelector('.schedule-desc').textContent;
            const technicianId = this.dataset.technicianId;
            const timeOff = this.dataset.timeOff === 'true';  // Add time off status

            // Set form values
            document.getElementById('schedule_id').value = scheduleId;
            document.getElementById('schedule_date').value = startTime.toISOString().split('T')[0];
            document.getElementById('start_hour').value = startTime.getHours().toString().padStart(2, '0');
            document.getElementById('end_hour').value = endTime.getHours().toString().padStart(2, '0');
            document.getElementById('description').value = description;
            document.getElementById('time_off').checked = timeOff;  // Set time off checkbox

            // Set technician if the select exists (admin only)
            const technicianSelect = document.getElementById('technician');
            if (technicianSelect) {
                technicianSelect.value = technicianId;
            }

            // Update modal title and buttons
            document.querySelector('.modal-title').textContent = 'Edit Schedule';
            document.querySelector('button[type="submit"]').textContent = 'Update Schedule';
            document.getElementById('delete_button').style.display = 'block';
            document.getElementById('copy_button').style.display = 'block';

            // Show the modal
            scheduleModal.show();
        });
    });

    // Handle copy button click
    document.getElementById('copy_button').addEventListener('click', function() {
        // Clear the schedule ID to create a new entry
        document.getElementById('schedule_id').value = '';

        // Update modal title and buttons
        document.querySelector('.modal-title').textContent = 'Copy Schedule';
        document.querySelector('button[type="submit"]').textContent = 'Add Copy';
        document.getElementById('delete_button').style.display = 'none';
        document.getElementById('copy_button').style.display = 'none';
    });

    // Handle time slot clicks
    document.querySelectorAll('.time-slot').forEach(slot => {
        slot.addEventListener('click', function() {
            const hour = this.dataset.hour;
            const date = this.closest('.day-slots').dataset.date;

            // Reset form
            document.getElementById('schedule_form').reset();
            document.getElementById('schedule_id').value = '';

            // Set the date and initial times
            document.getElementById('schedule_date').value = date;
            document.getElementById('start_hour').value = hour;

            // Update modal title and buttons
            document.querySelector('.modal-title').textContent = 'Add New Schedule';
            document.querySelector('button[type="submit"]').textContent = 'Add Schedule';
            document.getElementById('delete_button').style.display = 'none';
            document.getElementById('copy_button').style.display = 'none';

            // Show the modal
            scheduleModal.show();
        });
    });

    // Update end time options based on start time - Remove auto-update functionality
    window.updateEndTimeOptions = function() {
        const endSelect = document.getElementById('end_hour');
        // Clear existing options
        endSelect.innerHTML = '';

        // Add options for all 24 hours
        for (let hour = 0; hour < 24; hour++) {
            const option = document.createElement('option');
            option.value = hour.toString().padStart(2, '0');
            option.text = `${hour.toString().padStart(2, '0')}:00`;
            endSelect.appendChild(option);
        }
        // Add the 00:00 option at the end for next day
        const midnightOption = document.createElement('option');
        midnightOption.value = '00';
        midnightOption.text = '00:00';
        endSelect.appendChild(midnightOption);
    };

    // Remove the onchange handler from the start hour select
    const startHourSelect = document.getElementById('start_hour');
    if (startHourSelect) {
        startHourSelect.removeAttribute('onchange');
    }

    // Toggle repeat days section
    window.toggleRepeatDaysSelection = function() {
        const repeatDaysContainer = document.getElementById('repeat_days_container');
        const isChecked = document.getElementById('repeat_days_toggle').checked;
        
        repeatDaysContainer.style.display = isChecked ? 'block' : 'none';
        
        // If unchecking, clear all the checkboxes except the first one
        if (!isChecked) {
            const checkboxes = document.querySelectorAll('.repeat-day-checkbox');
            checkboxes.forEach((checkbox, index) => {
                if (index > 0) { // Skip the first one
                    checkbox.checked = false;
                }
            });
        }
    };

    // Handle form submission
    document.getElementById('schedule_form').addEventListener('submit', function(e) {
        e.preventDefault();

        const date = document.getElementById('schedule_date').value;
        const startHour = document.getElementById('start_hour').value;
        const endHour = document.getElementById('end_hour').value;
        const isRepeatEnabled = document.getElementById('repeat_days_toggle').checked;

        // Set the hidden datetime inputs for the first/main date
        document.getElementById('start_time_input').value = `${date} ${startHour}:00`;
        document.getElementById('end_time_input').value = `${date} ${endHour}:00`;
        
        // Handle repeat days if enabled
        if (isRepeatEnabled) {
            const selectedDays = [];
            const checkboxes = document.querySelectorAll('.repeat-day-checkbox:checked');
            
            checkboxes.forEach(checkbox => {
                selectedDays.push(checkbox.value);
            });
            
            if (selectedDays.length > 0) {
                document.getElementById('repeat_days_input').value = selectedDays.join(',');
            }
            
            console.log('Repeat days selection:', selectedDays);
        } else {
            // Clear the repeat days input
            document.getElementById('repeat_days_input').value = '';
        }

        console.log('Form submission:', {
            date: date,
            startHour: startHour,
            endHour: endHour,
            repeatEnabled: isRepeatEnabled,
            repeatDays: document.getElementById('repeat_days_input').value
        });

        // Submit the form
        this.submit();
    });

    // Handle delete button
    document.getElementById('delete_button').addEventListener('click', function() {
        if (confirm('Are you sure you want to delete this schedule?')) {
            const scheduleId = document.getElementById('schedule_id').value;
            window.location.href = `/schedule/delete/${scheduleId}`;
        }
    });

    // Initialize positions
    positionSchedules();

    // Update upcoming time off panel
    function updateUpcomingTimeOff() {
        const timeOffDiv = document.getElementById('upcoming-time-off');
        if (!timeOffDiv) return;

        fetch('/api/upcoming_time_off')
            .then(response => response.json())
            .then(entries => {
                if (entries.length === 0) {
                    timeOffDiv.innerHTML = '<p class="text-muted">No upcoming time off scheduled</p>';
                    return;
                }

                timeOffDiv.innerHTML = entries.map(entry => `
                    <div class="d-flex align-items-center mb-2">
                        <i data-feather="calendar" class="me-2"></i>
                        <div>
                            <strong>${entry.username}</strong>
                            <br>
                            <small class="text-muted">
                                ${entry.start_date} to ${entry.end_date}
                                <span class="badge bg-secondary ms-1">${entry.duration}</span>
                                ${entry.description ? `<br>${entry.description}` : ''}
                            </small>
                        </div>
                    </div>
                    <div class="border-bottom mb-2"></div>
                `).join('');

                // Initialize the newly added feather icons
                feather.replace();
            })
            .catch(error => {
                console.error('Error fetching time off entries:', error);
                timeOffDiv.innerHTML = '<p class="text-danger">Error loading time off entries</p>';
            });
    }

    // Update time off entries every minute along with active users
    updateUpcomingTimeOff();
    setInterval(updateUpcomingTimeOff, 60000);

    // Update active users panel
    function updateActiveUsers() {
        const activeUsersDiv = document.getElementById('active-users');
        if (!activeUsersDiv) return;

        fetch('/api/active_users')
            .then(response => response.json())
            .then(users => {
                if (users.length === 0) {
                    activeUsersDiv.innerHTML = '<p class="text-muted">No active technicians</p>';
                    return;
                }

                activeUsersDiv.innerHTML = users.map(user => `
                    <div class="d-flex align-items-center mb-2">
                        <span class="me-2" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${user.color}"></span>
                        <span>${user.username}</span>
                    </div>
                `).join('');
            })
            .catch(error => {
                console.error('Error fetching active users:', error);
                activeUsersDiv.innerHTML = '<p class="text-danger">Error loading active users</p>';
            });
    }

    // Update active users every minute
    updateActiveUsers(); // Call immediately when loaded
    setInterval(updateActiveUsers, 60000);
});