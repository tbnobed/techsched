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
            const locationId = this.dataset.locationId || '';  // Get location ID

            // Set form values
            document.getElementById('schedule_id').value = scheduleId;
            document.getElementById('schedule_date').value = startTime.toISOString().split('T')[0];
            document.getElementById('start_hour').value = startTime.getHours().toString().padStart(2, '0');
            document.getElementById('end_hour').value = endTime.getHours().toString().padStart(2, '0');
            document.getElementById('description').value = description;
            document.getElementById('time_off').checked = timeOff;  // Set time off checkbox
            
            // Set location if the select exists
            const locationSelect = document.getElementById('location_id');
            if (locationSelect && locationId) {
                locationSelect.value = locationId;
            }

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

    // Mini-calendar for repeat days selection
    let currentDate = new Date();
    let selectedDates = new Set(); // Use a Set to store selected dates
    let currentMonth = currentDate.getMonth();
    let currentYear = currentDate.getFullYear();
    let primaryDate = null; // The main date selected in the schedule form
    
    // Toggle repeat days section
    window.toggleRepeatDaysSelection = function() {
        const repeatDaysContainer = document.getElementById('repeat_days_container');
        const isChecked = document.getElementById('repeat_days_toggle').checked;
        
        repeatDaysContainer.style.display = isChecked ? 'block' : 'none';
        
        if (isChecked) {
            // Initialize the calendar
            initMiniCalendar();
        } else {
            // Clear selections except for the primary date
            clearDateSelection(true);
        }
    };
    
    // Initialize the mini-calendar
    function initMiniCalendar() {
        // Set the primary date from the date input
        const dateInput = document.getElementById('schedule_date');
        primaryDate = dateInput.value;
        
        // Update month/year display
        updateCalendarHeader();
        
        // Generate calendar days
        generateCalendarDays();
        
        // Add event listeners for navigation
        document.getElementById('prev-month').addEventListener('click', function() {
            navigateMonth(-1);
        });
        
        document.getElementById('next-month').addEventListener('click', function() {
            navigateMonth(1);
        });
        
        // Clear selection button
        document.getElementById('clear-selection').addEventListener('click', function() {
            clearDateSelection();
        });
    }
    
    // Update the calendar header (month and year)
    function updateCalendarHeader() {
        const monthNames = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ];
        
        document.getElementById('calendar-month-year').textContent = 
            `${monthNames[currentMonth]} ${currentYear}`;
    }
    
    // Generate calendar days for the current month
    function generateCalendarDays() {
        const calendarDays = document.getElementById('calendar-days');
        calendarDays.innerHTML = '';
        
        // Create a date object for the first day of the current month
        const firstDay = new Date(currentYear, currentMonth, 1);
        const lastDay = new Date(currentYear, currentMonth + 1, 0);
        
        // Get the day of the week the month starts on (0 = Sunday, 6 = Saturday)
        const startingDayOfWeek = firstDay.getDay();
        
        // Get number of days in the current month
        const daysInMonth = lastDay.getDate();
        
        // Get today's date for highlighting
        const today = new Date();
        const todayFormatted = formatDate(today);
        
        // Add the days from the previous month to fill the first row
        const prevMonthLastDay = new Date(currentYear, currentMonth, 0).getDate();
        for (let i = startingDayOfWeek - 1; i >= 0; i--) {
            const day = prevMonthLastDay - i;
            const date = new Date(currentYear, currentMonth - 1, day);
            const dateFormatted = formatDate(date);
            
            addDayToCalendar(calendarDays, day, dateFormatted, 'outside-month', 
                dateFormatted === todayFormatted, 
                dateFormatted === primaryDate,
                selectedDates.has(dateFormatted));
        }
        
        // Add the days of the current month
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(currentYear, currentMonth, day);
            const dateFormatted = formatDate(date);
            
            addDayToCalendar(calendarDays, day, dateFormatted, '', 
                dateFormatted === todayFormatted, 
                dateFormatted === primaryDate,
                selectedDates.has(dateFormatted));
        }
        
        // Add days from the next month to complete the grid (always show 6 rows)
        const totalCells = 42; // 6 rows x 7 columns
        const cellsToAdd = totalCells - (startingDayOfWeek + daysInMonth);
        
        for (let day = 1; day <= cellsToAdd; day++) {
            const date = new Date(currentYear, currentMonth + 1, day);
            const dateFormatted = formatDate(date);
            
            addDayToCalendar(calendarDays, day, dateFormatted, 'outside-month', 
                dateFormatted === todayFormatted, 
                dateFormatted === primaryDate,
                selectedDates.has(dateFormatted));
        }
    }
    
    // Add a day to the calendar
    function addDayToCalendar(container, day, dateFormatted, extraClass, isToday, isPrimary, isSelected) {
        const dayItem = document.createElement('div');
        dayItem.textContent = day;
        dayItem.className = `day-item${extraClass ? ' ' + extraClass : ''}${isToday ? ' today' : ''}${isPrimary ? ' primary-date' : ''}${isSelected ? ' selected' : ''}`;
        dayItem.dataset.date = dateFormatted;
        
        // Add click event to toggle selection
        dayItem.addEventListener('click', function() {
            // Don't allow selection/deselection of the primary date
            if (dateFormatted === primaryDate) {
                return;
            }
            
            // Toggle selection
            if (selectedDates.has(dateFormatted)) {
                selectedDates.delete(dateFormatted);
                this.classList.remove('selected');
            } else {
                selectedDates.add(dateFormatted);
                this.classList.add('selected');
            }
            
            // Update the hidden input with selected dates
            updateSelectedDatesInput();
        });
        
        container.appendChild(dayItem);
    }
    
    // Format a date as YYYY-MM-DD
    function formatDate(date) {
        const year = date.getFullYear();
        const month = (date.getMonth() + 1).toString().padStart(2, '0');
        const day = date.getDate().toString().padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Navigate to previous or next month
    function navigateMonth(offset) {
        currentMonth += offset;
        
        // Handle year change
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        } else if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        
        // Update the calendar
        updateCalendarHeader();
        generateCalendarDays();
    }
    
    // Clear date selection (optionally keeping the primary date)
    function clearDateSelection(keepPrimary = false) {
        if (keepPrimary) {
            selectedDates.clear();
            // Keep primary date if it exists
            if (primaryDate) {
                selectedDates.add(primaryDate);
            }
        } else {
            selectedDates.clear();
        }
        
        // Update the hidden input
        updateSelectedDatesInput();
        
        // Refresh the calendar display
        generateCalendarDays();
    }
    
    // Update the hidden input with the selected dates for form submission
    function updateSelectedDatesInput() {
        const datesArray = Array.from(selectedDates);
        document.getElementById('repeat_days_list').value = datesArray.join(',');
        
        // Also update a display of selected dates count
        const selectedCount = document.getElementById('selected-dates-count');
        if (selectedCount) {
            const count = selectedDates.size - (selectedDates.has(primaryDate) ? 1 : 0);
            selectedCount.textContent = count > 0 ? `${count} additional date${count !== 1 ? 's' : ''} selected` : 'No additional dates selected';
        }
    }
    
    // Check if the mini-calendar exists before initializing
    if (document.getElementById('repeat_days_container')) {
        // If the toggle is checked by default, initialize the calendar
        if (document.getElementById('repeat_days_toggle').checked) {
            initMiniCalendar();
        }
    }
    
    // Initialize the direct date selector toggle if it exists
    const directDateToggle = document.getElementById('direct_date_toggle');
    if (directDateToggle) {
        directDateToggle.addEventListener('change', function() {
            document.getElementById('direct_date_selector').style.display = 
                this.checked ? 'block' : 'none';
        });
    }

    // Run position schedules on load
    positionSchedules();
    
    // Run it again after a small delay to ensure all elements are fully rendered
    setTimeout(positionSchedules, 100);
});
