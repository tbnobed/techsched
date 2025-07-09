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

            // Position overlapping events horizontally - evenly distribute across column width
            overlappingGroups.forEach(group => {
                if (group.length > 1) {
                    // Check if events start at exactly the same time
                    const firstEventStart = new Date(group[0].dataset.startTime);
                    const allSameStartTime = group.every(event => {
                        const eventStart = new Date(event.dataset.startTime);
                        return eventStart.getTime() === firstEventStart.getTime();
                    });
                    
                    if (allSameStartTime) {
                        // Events start at same time - divide evenly across column width
                        const eventWidth = 100 / group.length;
                        group.forEach((event, index) => {
                            event.style.width = `${eventWidth - 1}%`; // Subtract 1% for spacing
                            event.style.left = `${index * eventWidth}%`;
                            event.style.right = 'auto';
                            event.style.boxSizing = 'border-box';
                            event.style.zIndex = 10 + index;
                        });
                    } else {
                        // Events start at different times - use offset positioning
                        const offsetStep = 8; // Fixed 8% offset between events
                        
                        group.forEach((event, index) => {
                            const leftPosition = index * offsetStep;
                            
                            // Measure the text width in the header
                            const headerElement = event.querySelector('.schedule-header');
                            if (headerElement) {
                                // Create a temporary element to measure text width
                                const tempElement = document.createElement('span');
                                tempElement.style.visibility = 'hidden';
                                tempElement.style.position = 'absolute';
                                tempElement.style.whiteSpace = 'nowrap';
                                tempElement.style.fontSize = window.getComputedStyle(headerElement).fontSize;
                                tempElement.style.fontFamily = window.getComputedStyle(headerElement).fontFamily;
                                tempElement.style.fontWeight = window.getComputedStyle(headerElement).fontWeight;
                                tempElement.textContent = headerElement.textContent;
                                
                                document.body.appendChild(tempElement);
                                const textWidth = tempElement.offsetWidth;
                                document.body.removeChild(tempElement);
                                
                                // Calculate width based on text, with some padding
                                const parentWidth = event.parentElement.offsetWidth;
                                const textWidthPercent = ((textWidth + 16) / parentWidth) * 100; // Add 16px padding
                                const minWidth = 60; // Minimum 60% width
                                const maxWidth = Math.min(95, 100 - leftPosition); // Stay within bounds
                                const calculatedWidth = Math.max(minWidth, Math.min(textWidthPercent, maxWidth));
                                
                                event.style.width = `${calculatedWidth}%`;
                            } else {
                                // Fallback to fixed width if no header found
                                const maxWidth = 100 - leftPosition;
                                event.style.width = `${Math.min(75, maxWidth)}%`;
                            }
                            
                            event.style.left = `${leftPosition}%`;
                            event.style.right = 'auto';
                            event.style.boxSizing = 'border-box';
                            event.style.zIndex = 10 + index;
                        });
                    }
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
            const descElement = this.querySelector('.schedule-desc');
            const description = descElement ? descElement.textContent : '';
            const technicianId = this.dataset.technicianId;
            const timeOff = this.dataset.timeOff === 'true';  // Add time off status
            
            // Set form values
            document.getElementById('schedule_id').value = scheduleId;
            
            // Fix for date display - adjust for timezone issues
            // Use the date from the data attribute directly without timezone conversion
            const startTimeStr = this.dataset.startTime.split(' ')[0]; // Get YYYY-MM-DD portion
            
            document.getElementById('schedule_date').value = startTimeStr;
            document.getElementById('start_hour').value = startTime.getHours().toString().padStart(2, '0');
            document.getElementById('end_hour').value = endTime.getHours().toString().padStart(2, '0');
            document.getElementById('description').value = description;
            
            // Handle time off checkbox if it exists
            const timeOffCheckbox = document.getElementById('time_off');
            if (timeOffCheckbox) {
                timeOffCheckbox.checked = timeOff;
            }
            
            // Set technician if the select exists (admin only)
            const technicianSelect = document.getElementById('technician');
            if (technicianSelect) {
                technicianSelect.value = technicianId;
            }
            
            // Set location if it exists
            // We need to find the location ID from the location element
            const locationElement = this.querySelector('.schedule-location');
            if (locationElement && locationElement.textContent) {
                const locationText = locationElement.textContent.trim();
                // Find the location select and set it to the proper location if found
                const locationSelect = document.getElementById('location_id');
                if (locationSelect) {
                    console.log("Setting location from:", locationText);
                    
                    // Try to find the matching location option
                    let locationFound = false;
                    for (let i = 0; i < locationSelect.options.length; i++) {
                        if (locationSelect.options[i].text.trim() === locationText) {
                            locationSelect.selectedIndex = i;
                            locationFound = true;
                            console.log("Location matched:", locationSelect.options[i].text);
                            break;
                        }
                    }
                    
                    if (!locationFound) {
                        console.log("No matching location found in dropdown for:", locationText);
                    }
                }
            } else {
                console.log("No location element found, setting to default Plex location");
                const locationSelect = document.getElementById('location_id');
                if (locationSelect) {
                    // Find the Plex option
                    for (let i = 0; i < locationSelect.options.length; i++) {
                        if (locationSelect.options[i].text.trim() === 'Plex') {
                            locationSelect.selectedIndex = i;
                            break;
                        }
                    }
                }
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
            
            // Set default location to Plex
            const locationSelect = document.getElementById('location_id');
            if (locationSelect) {
                // First try to find "Plex" (ID 1)
                for (let i = 0; i < locationSelect.options.length; i++) {
                    if (locationSelect.options[i].text.trim() === 'Plex') {
                        locationSelect.selectedIndex = i;
                        console.log("Setting default location to Plex");
                        break;
                    }
                }
            }

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
        dayItem.className = `day-item${extraClass ? ' ' + extraClass : ''}${isToday ? ' today' : ''}`;
        
        if (isPrimary) {
            dayItem.classList.add('primary-date');
            dayItem.setAttribute('title', 'Primary schedule date');
        } else if (isSelected) {
            dayItem.classList.add('selected');
        }
        
        dayItem.setAttribute('data-date', dateFormatted);
        
        // Add click event to select/deselect the date
        if (!isPrimary) { // Don't allow clicking on the primary date
            dayItem.addEventListener('click', function() {
                toggleDateSelection(dateFormatted, dayItem);
            });
        } else {
            dayItem.classList.add('disabled');
        }
        
        container.appendChild(dayItem);
    }
    
    // Toggle date selection
    function toggleDateSelection(dateStr, dayItem) {
        if (selectedDates.has(dateStr)) {
            // Deselect the date
            selectedDates.delete(dateStr);
            dayItem.classList.remove('selected');
        } else {
            // Select the date
            selectedDates.add(dateStr);
            dayItem.classList.add('selected');
        }
        
        // Update the display of selected dates
        updateSelectedDatesDisplay();
        
        // Update the hidden input
        updateRepeatDaysInput();
    }
    
    // Update the display of selected dates
    function updateSelectedDatesDisplay() {
        const container = document.getElementById('selected-dates-container');
        
        if (selectedDates.size === 0) {
            container.innerHTML = '<span class="text-muted" id="no-dates-selected">No additional dates selected</span>';
            return;
        }
        
        // Sort the dates
        const sortedDates = Array.from(selectedDates).sort();
        container.innerHTML = '';
        
        // Add date tags
        sortedDates.forEach(dateStr => {
            const dateObj = parseDate(dateStr);
            
            const dateTag = document.createElement('div');
            dateTag.className = 'date-tag';
            
            // Format the date nicely (e.g., "Mon 03/27")
            const dateLabel = document.createElement('span');
            dateLabel.textContent = new Date(dateObj).toLocaleDateString('en-US', { 
                weekday: 'short', 
                month: '2-digit',
                day: '2-digit'
            });
            
            // Add a remove button
            const closeBtn = document.createElement('span');
            closeBtn.className = 'close ms-2';
            closeBtn.innerHTML = '&times;';
            closeBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                removeDateSelection(dateStr);
            });
            
            dateTag.appendChild(dateLabel);
            dateTag.appendChild(closeBtn);
            container.appendChild(dateTag);
        });
    }
    
    // Remove a specific date from the selection
    function removeDateSelection(dateStr) {
        selectedDates.delete(dateStr);
        
        // Update the calendar if the date is currently visible
        const dayItem = document.querySelector(`.day-item[data-date="${dateStr}"]`);
        if (dayItem) {
            dayItem.classList.remove('selected');
        }
        
        // Update the display
        updateSelectedDatesDisplay();
        
        // Update the hidden input
        updateRepeatDaysInput();
    }
    
    // Clear all selected dates
    function clearDateSelection(keepHidden = false) {
        selectedDates.clear();
        
        // Remove selected class from all visible days
        document.querySelectorAll('.day-item.selected').forEach(item => {
            item.classList.remove('selected');
        });
        
        // Update the display
        updateSelectedDatesDisplay();
        
        // Update the hidden input
        if (!keepHidden) {
            updateRepeatDaysInput();
        }
    }
    
    // Update the hidden input with selected dates
    function updateRepeatDaysInput() {
        const allDates = new Set(selectedDates);
        
        // Include the primary date
        if (primaryDate) {
            allDates.add(primaryDate);
        }
        
        // Update the hidden input
        if (allDates.size > 0) {
            document.getElementById('repeat_days_input').value = Array.from(allDates).sort().join(',');
        } else {
            document.getElementById('repeat_days_input').value = '';
        }
    }
    
    // Navigate to previous/next month
    function navigateMonth(direction) {
        currentMonth += direction;
        
        if (currentMonth < 0) {
            currentMonth = 11;
            currentYear--;
        } else if (currentMonth > 11) {
            currentMonth = 0;
            currentYear++;
        }
        
        updateCalendarHeader();
        generateCalendarDays();
    }
    
    // Format date as YYYY-MM-DD
    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }
    
    // Parse date string YYYY-MM-DD
    function parseDate(dateStr) {
        const [year, month, day] = dateStr.split('-').map(Number);
        return new Date(year, month - 1, day);
    }

    // Handle form submission
    document.getElementById('schedule_form').addEventListener('submit', function(e) {
        e.preventDefault();

        const date = document.getElementById('schedule_date').value;
        const startHour = document.getElementById('start_hour').value;
        const endHour = document.getElementById('end_hour').value;
        const isRepeatEnabled = document.getElementById('repeat_days_toggle').checked;

        // Update the primary date in case it changed
        primaryDate = date;
        
        // Set the hidden datetime inputs for the first/main date
        document.getElementById('start_time_input').value = `${date} ${startHour}:00`;
        document.getElementById('end_time_input').value = `${date} ${endHour}:00`;
        
        // Handle repeat days if enabled
        if (isRepeatEnabled) {
            // Update the repeat days input with all selected dates
            updateRepeatDaysInput();
            
            // Log selection for debugging
            console.log('Repeat days selection:', Array.from(selectedDates));
        } else {
            // Clear the repeat days input
            document.getElementById('repeat_days_input').value = '';
        }

        // Make sure the primary date is included in the input
        // But only if we have at least one additional day selected
        if (isRepeatEnabled && selectedDates.size > 0) {
            let currentValue = document.getElementById('repeat_days_input').value;
            if (!currentValue.includes(primaryDate)) {
                if (currentValue) {
                    currentValue += ',';
                }
                currentValue += primaryDate;
                document.getElementById('repeat_days_input').value = currentValue;
            }
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
            
            // Get the current week_start from the URL
            const urlParams = new URLSearchParams(window.location.search);
            const weekStart = urlParams.get('week_start');
            
            // Check if we're in personal view
            const isPersonalView = window.location.pathname.includes('/personal_schedule');
            const deletePath = isPersonalView ? '/schedule/delete/' : '/schedule/delete/';
            
            // Redirect with the week_start parameter to maintain the same view
            if (weekStart) {
                window.location.href = `${deletePath}${scheduleId}?week_start=${weekStart}${isPersonalView ? '&personal_view=true' : ''}`;
            } else {
                window.location.href = `${deletePath}${scheduleId}${isPersonalView ? '?personal_view=true' : ''}`;
            }
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
                    <div class="time-off-entry p-3 mb-3" 
                         style="border-left: 4px solid ${entry.color || '#6c757d'};">
                        <div class="d-flex align-items-top">
                            <i data-feather="calendar" class="me-2 mt-1"></i>
                            <div>
                                <strong>${entry.username}</strong>
                                <br>
                                <small>
                                    ${entry.start_date} to ${entry.end_date}
                                    <span class="badge bg-danger ms-1">${entry.duration}</span>
                                </small>
                                ${entry.description ? `<div class="mt-1 small">${entry.description}</div>` : ''}
                            </div>
                        </div>
                    </div>
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
                    <div class="active-user-entry d-flex align-items-center mb-3 p-2" 
                         style="border-left: 4px solid ${user.color};">
                        <span class="me-2" style="width: 12px; height: 12px; border-radius: 50%; background-color: ${user.color}"></span>
                        <span class="fw-medium">${user.username}</span>
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
    
    // Current time line functionality
    function updateCurrentTimeLine() {
        const timeLines = document.querySelectorAll('.current-time-line');
        if (timeLines.length === 0) return;
        
        // Get current time in user's timezone
        const now = new Date();
        const userTimezone = window.userTimezone || 'UTC';
        
        // Create time in user's timezone using Intl API
        let currentHour, currentMinute, timeString;
        
        try {
            // Get the current time in the user's timezone
            const timeInUserTimezone = new Intl.DateTimeFormat('en-US', {
                timeZone: userTimezone,
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            }).format(now);
            
            // Parse the formatted time
            const [hour, minute] = timeInUserTimezone.split(':').map(Number);
            currentHour = hour;
            currentMinute = minute;
            
            // Format time for display
            timeString = new Intl.DateTimeFormat('en-US', {
                timeZone: userTimezone,
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            }).format(now);
            
        } catch (error) {
            console.warn('Error getting time in user timezone, falling back to local time:', error);
            // Fallback to local time
            currentHour = now.getHours();
            currentMinute = now.getMinutes();
            timeString = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        }
        
        // Calculate position: each hour is 60px, so we need to find the exact position
        const hourPixels = 60; // Height of each hour slot
        const totalMinutes = currentHour * 60 + currentMinute;
        const topPosition = (totalMinutes / 60) * hourPixels;
        
        timeLines.forEach(timeLine => {
            timeLine.style.top = `${topPosition}px`;
            timeLine.style.display = 'block';
            timeLine.setAttribute('data-time', timeString);
        });
    }
    
    // Initialize current time line and update it every minute
    updateCurrentTimeLine();
    setInterval(updateCurrentTimeLine, 60000);
});