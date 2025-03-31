document.addEventListener('DOMContentLoaded', function() {
    // Initialize Feather icons
    feather.replace();

    // Initialize Bootstrap modal
    const scheduleModal = new bootstrap.Modal(document.getElementById('scheduleModal'));
    
    // Initialize AJAX-based calendar navigation
    const calendarContainer = document.querySelector('.calendar-container');
    if (calendarContainer) {
        const isPersonalView = calendarContainer.dataset.personalView === 'true';
        
        // Set up navigation buttons
        document.querySelectorAll('.nav-week').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const weekStart = this.dataset.weekStart;
                loadCalendarData(weekStart, isPersonalView);
            });
        });
        
        // Set up month navigation buttons
        document.querySelectorAll('.nav-month').forEach(link => {
            link.addEventListener('click', function(e) {
                e.preventDefault();
                const weekStart = this.dataset.weekStart;
                loadCalendarData(weekStart, isPersonalView);
            });
        });
    }

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

    // AJAX-based navigation for calendar
    window.loadCalendarData = function(weekStart, isPersonalView) {
        console.log('Loading calendar data:', weekStart, 'isPersonal:', isPersonalView, 'isMobile:', isMobileDevice());
        
        // Show a loading indicator
        const loadingOverlay = document.createElement('div');
        loadingOverlay.className = 'loading-overlay';
        loadingOverlay.innerHTML = '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading...</span></div>';
        document.body.appendChild(loadingOverlay);
        
        // Build the query parameters
        let params = new URLSearchParams();
        if (weekStart) {
            params.append('week_start', weekStart);
        }
        
        const locationFilter = document.getElementById('location-filter');
        if (locationFilter && locationFilter.value) {
            params.append('location_id', locationFilter.value);
        }
        
        if (isPersonalView) {
            params.append('personal_view', '1');
        }
        
        // Make the AJAX request
        fetch('/api/calendar_data?' + params.toString())
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                console.log('Calendar data received:', data);
                
                // Update date range display
                updateDateRangeDisplay(data.date_range);
                
                // Update navigation links
                updateNavigationLinks(data.date_range, isPersonalView);
                
                // Update the schedule display based on device type and UI container
                const mobileCalendar = document.querySelector('.mobile-calendar');
                if (mobileCalendar) {
                    console.log('Mobile calendar found, updating mobile view');
                    updateMobileScheduleDisplay(data.days);
                } else {
                    console.log('Desktop calendar found, updating desktop view');
                    updateDesktopScheduleDisplay(data.schedules, data.days);
                }
                
                // Remove loading overlay
                document.body.removeChild(loadingOverlay);
            })
            .catch(error => {
                console.error('Error fetching calendar data:', error);
                // Remove loading overlay
                document.body.removeChild(loadingOverlay);
                // Show error message
                alert('Failed to load calendar data. Please try again.');
            });
    };
    
    // Function to update date range display
    function updateDateRangeDisplay(dateRange) {
        const dateRangeElement = document.getElementById('current-date-range');
        if (dateRangeElement) {
            dateRangeElement.textContent = `${dateRange.week_start_display} - ${dateRange.week_end_display}`;
        }
    }
    
    // Function to update navigation links
    function updateNavigationLinks(dateRange, isPersonalView) {
        // Update next/previous week buttons for mobile view
        window.previousWeek = function() {
            loadCalendarData(dateRange.prev_week, isPersonalView);
        };
        
        window.nextWeek = function() {
            loadCalendarData(dateRange.next_week, isPersonalView);
        };
    }
    
    // Function to update mobile schedule display
    function updateMobileScheduleDisplay(days) {
        const mobileCalendar = document.querySelector('.mobile-calendar');
        if (!mobileCalendar) return;
        
        // Get personal view setting
        const isPersonalView = mobileCalendar.dataset.personalView === 'true';
        console.log('Mobile calendar personal view:', isPersonalView);
        
        // Update date range in header
        const dateRangeElem = document.getElementById('current-date-range');
        if (dateRangeElem && days && days.length >= 7) {
            const startDay = days[0];
            const endDay = days[6];
            if (startDay && endDay) {
                dateRangeElem.textContent = `${startDay.date_str} - ${endDay.date_str}`;
            }
        }
        
        // Update day tabs
        const daySelector = document.querySelector('.day-selector ul');
        if (daySelector && days) {
            // Clear existing tabs
            daySelector.innerHTML = '';
            
            // Create new tabs
            days.forEach((day, index) => {
                const isToday = day.is_today || index === 0; // Default to first day if no today
                const dayDate = new Date(day.date);
                
                const tab = document.createElement('li');
                tab.className = 'nav-item';
                tab.innerHTML = `
                    <button class="nav-link ${isToday ? 'active' : ''}" 
                            onclick="showDay(${index})"
                            data-day="${index}">
                        ${dayDate.toLocaleDateString('en-US', {weekday: 'short'})}<br>
                        <span class="day-number">${dayDate.getDate()}</span>
                    </button>
                `;
                daySelector.appendChild(tab);
            });
        }
        
        console.log('Updating mobile day containers, days:', days);
        
        // Update day containers
        for (let i = 0; i < days.length; i++) {
            const day = days[i];
            const dayContainer = document.getElementById(`day-${i}`);
            if (dayContainer) {
                console.log(`Processing day ${i}:`, day);
                
                // Update day header
                const dayHeader = dayContainer.querySelector('.day-header h4');
                if (dayHeader) {
                    const dayDate = new Date(day.date);
                    dayHeader.textContent = dayDate.toLocaleDateString('en-US', {
                        weekday: 'long', 
                        year: 'numeric', 
                        month: 'long', 
                        day: 'numeric'
                    });
                }
                
                // Update schedules
                const schedulesContainer = dayContainer.querySelector('.day-schedules');
                if (schedulesContainer) {
                    // Clear existing schedules
                    schedulesContainer.innerHTML = '';
                    
                    // Add schedules for this day
                    let hasSchedules = false;
                    
                    // Ensure schedules is an array before iterating
                    const schedules = day.schedules || [];
                    console.log(`Day ${i} schedules:`, schedules);
                    
                    schedules.forEach(schedule => {
                        hasSchedules = true;
                        const scheduleCard = document.createElement('div');
                        scheduleCard.className = 'mobile-schedule-card';
                        scheduleCard.style.setProperty('--tech-color', schedule.color || '#3498db');
                        scheduleCard.dataset.scheduleId = schedule.id;
                        scheduleCard.dataset.startTime = schedule.start_time;
                        scheduleCard.dataset.endTime = schedule.end_time;
                        scheduleCard.dataset.timeOff = schedule.time_off ? 'true' : 'false';
                        
                        // Format times
                        const startTime = new Date(schedule.start_time);
                        const endTime = new Date(schedule.end_time);
                        const timeFormatOptions = {hour: 'numeric', minute: '2-digit', hour12: true};
                        
                        // Build card content
                        let cardContent = `
                            <div class="schedule-time">
                                ${startTime.toLocaleTimeString('en-US', timeFormatOptions)} - 
                                ${endTime.toLocaleTimeString('en-US', timeFormatOptions)}
                            </div>
                        `;
                        
                        // Add technician name for non-personal view
                        if (!isPersonalView) {
                            cardContent += `
                                <div class="schedule-tech">
                                    ${schedule.technician_name}
                                </div>
                            `;
                        }
                        
                        // Add location if available
                        if (schedule.location) {
                            cardContent += `
                                <div class="schedule-location">
                                    <i data-feather="map-pin" class="feather-small"></i> ${schedule.location}
                                </div>
                            `;
                        }
                        
                        // Add time off badge if needed
                        if (schedule.time_off) {
                            cardContent += `
                                <div class="time-off-badge">
                                    <span class="badge bg-warning">Time Off</span>
                                </div>
                            `;
                        }
                        
                        // Add description if available
                        if (schedule.description) {
                            cardContent += `
                                <div class="schedule-desc">
                                    ${schedule.description}
                                </div>
                            `;
                        }
                        
                        scheduleCard.innerHTML = cardContent;
                        scheduleCard.setAttribute('data-bs-toggle', 'modal');
                        scheduleCard.setAttribute('data-bs-target', '#scheduleModal');
                        
                        schedulesContainer.appendChild(scheduleCard);
                    });
                    
                    // Show empty message if no schedules
                    if (!hasSchedules) {
                        const dayDate = new Date(day.date);
                        const emptyMessage = document.createElement('div');
                        emptyMessage.className = 'empty-day-message';
                        emptyMessage.innerHTML = `
                            <p>No schedules for this day.</p>
                            <button class="btn btn-sm btn-outline-primary" 
                                    data-bs-toggle="modal" 
                                    data-bs-target="#scheduleModal"
                                    data-date="${day.date}">
                                Add Schedule
                            </button>
                        `;
                        schedulesContainer.appendChild(emptyMessage);
                    }
                }
            }
        }
        
        // Initialize feather icons for the new content
        if (typeof feather !== 'undefined') {
            feather.replace({
                'stroke-width': 1.5,
                'width': 16,
                'height': 16
            });
        }
    }
    
    // Function to detect mobile device
    function isMobileDevice() {
        return window.innerWidth < 768 || 
               /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    // Function to update desktop schedule display
    function updateDesktopScheduleDisplay(schedules, days) {
        // Clear existing schedule cards
        document.querySelectorAll('.schedule-card').forEach(card => {
            card.remove();
        });
        
        // Create updated schedule cards
        schedules.forEach(schedule => {
            createScheduleCard(schedule);
        });
        
        // Update day headers with new dates
        if (days && days.length > 0) {
            const dayHeaders = document.querySelectorAll('.day-header');
            days.forEach((day, index) => {
                if (dayHeaders[index]) {
                    dayHeaders[index].innerHTML = day.display_date;
                    
                    // Add today class to current day
                    if (day.is_today) {
                        dayHeaders[index].closest('.day-column').classList.add('today');
                    } else {
                        dayHeaders[index].closest('.day-column').classList.remove('today');
                    }
                }
            });
        }
        
        // Re-run positioning
        positionSchedules();
        
        // Reinitialize feather icons if present
        if (typeof feather !== 'undefined') {
            feather.replace();
        }
    }
    
    // Function to create a schedule card for the desktop view
    function createScheduleCard(schedule) {
        const scheduleDate = new Date(schedule.start_time_raw);
        const dayOfWeek = scheduleDate.getDay();
        
        // Find the appropriate day column
        const dayColumn = document.querySelector(`.day-column[data-day="${dayOfWeek}"]`);
        if (!dayColumn) return;
        
        // Create the schedule card
        const card = document.createElement('div');
        card.className = 'schedule-card';
        card.setAttribute('data-schedule-id', schedule.id);
        card.setAttribute('data-start-time', schedule.start_time_raw);
        card.setAttribute('data-end-time', schedule.end_time_raw);
        card.setAttribute('data-time-off', schedule.time_off);
        
        // Calculate card position and height
        const startHour = new Date(schedule.start_time_raw).getHours();
        const endHour = new Date(schedule.end_time_raw).getHours() || 24; // Treat 0 as 24 (midnight)
        const startMinutes = new Date(schedule.start_time_raw).getMinutes();
        const endMinutes = new Date(schedule.end_time_raw).getMinutes();
        
        const topPosition = (startHour + startMinutes / 60) * 60;
        const height = (endHour + endMinutes / 60 - startHour - startMinutes / 60) * 60;
        
        card.style.top = topPosition + 'px';
        card.style.height = height + 'px';
        card.style.borderLeftColor = schedule.color;
        
        // Create the card content
        card.innerHTML = `
            <div class="card-title">${schedule.username}</div>
            <div class="card-time">${schedule.start_time} - ${schedule.end_time}</div>
            ${schedule.location_name ? `<div class="card-location"><i data-feather="map-pin"></i> ${schedule.location_name}</div>` : ''}
            ${schedule.description ? `<div class="card-description">${schedule.description}</div>` : ''}
        `;
        
        // Add click handler to open modal
        card.addEventListener('click', function() {
            // Get modal elements
            const scheduleModal = document.getElementById('scheduleModal');
            const scheduleId = document.getElementById('schedule_id');
            const scheduleDate = document.getElementById('schedule_date');
            const startHour = document.getElementById('start_hour');
            const endHour = document.getElementById('end_hour');
            const description = document.getElementById('description');
            const locationId = document.getElementById('location_id');
            const timeOff = document.getElementById('time_off');
            const modalTitle = document.querySelector('#scheduleModal .modal-title');
            const deleteButton = document.getElementById('delete_button');
            const submitButton = document.querySelector('#scheduleModal .btn-primary');
            
            // Populate modal with schedule data
            scheduleId.value = schedule.id;
            
            // Format date for input
            const dateObj = new Date(schedule.start_time_raw);
            const formattedDate = dateObj.toISOString().split('T')[0];
            scheduleDate.value = formattedDate;
            
            // Set hours
            if (startHour) {
                startHour.value = String(dateObj.getHours()).padStart(2, '0');
            }
            
            if (endHour) {
                const endDateObj = new Date(schedule.end_time_raw);
                const displayEndHour = endDateObj.getHours() === 0 ? '00' : String(endDateObj.getHours()).padStart(2, '0');
                endHour.value = displayEndHour;
            }
            
            // Set description
            description.value = schedule.description || '';
            
            // Set location if exists
            if (locationId && schedule.location_id) {
                locationId.value = schedule.location_id;
            } else if (locationId) {
                locationId.value = '';
            }
            
            // Set time off
            if (timeOff) {
                timeOff.checked = schedule.time_off === 'true' || schedule.time_off === true;
                
                // Toggle related UI if needed
                if (typeof toggleRepeatDaysSelection === 'function') {
                    toggleRepeatDaysSelection();
                }
            }
            
            // Update modal title and buttons
            modalTitle.textContent = 'Edit Schedule';
            deleteButton.style.display = 'block';
            submitButton.textContent = 'Save Changes';
            
            // Set up delete button
            deleteButton.onclick = function() {
                if (confirm('Are you sure you want to delete this schedule?')) {
                    const weekStart = new URLSearchParams(window.location.search).get('week_start') || '';
                    window.location.href = `/schedule/delete/${schedule.id}?week_start=${weekStart}`;
                }
            };
            
            // Open modal
            const modal = new bootstrap.Modal(scheduleModal);
            modal.show();
        });
        
        // Add to day column
        dayColumn.appendChild(card);
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