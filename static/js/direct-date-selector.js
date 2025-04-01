/**
 * Direct Date Selector
 * 
 * A specialized calendar date selector that avoids timezone issues
 * by directly working with the year, month, day components.
 */

// Global state
let directSelectedDates = new Set(); // Store selected dates
let directPrimaryDate = null; // Main schedule date
let directCurrentMonth = new Date().getMonth();
let directCurrentYear = new Date().getFullYear();

/**
 * Initialize the direct calendar 
 * @param {string} containerId - The ID of the container element
 * @param {string} primaryDateStr - The primary date in YYYY-MM-DD format
 */
function initDirectCalendar(containerId, primaryDateStr = null) {
    directPrimaryDate = primaryDateStr;
    
    // Initialize buttons
    document.getElementById('direct-prev-month-btn').addEventListener('click', function() {
        directPrevMonth();
    });
    
    document.getElementById('direct-next-month-btn').addEventListener('click', function() {
        directNextMonth();
    });
    
    // Generate the calendar
    directUpdateCalendarHeader();
    directGenerateCalendarDays();
}

/**
 * Move to the previous month
 */
function directPrevMonth() {
    directCurrentMonth--;
    if (directCurrentMonth < 0) {
        directCurrentMonth = 11;
        directCurrentYear--;
    }
    directUpdateCalendarHeader();
    directGenerateCalendarDays();
}

/**
 * Move to the next month
 */
function directNextMonth() {
    directCurrentMonth++;
    if (directCurrentMonth > 11) {
        directCurrentMonth = 0;
        directCurrentYear++;
    }
    directUpdateCalendarHeader();
    directGenerateCalendarDays();
}

/**
 * Update the calendar header with the current month and year
 */
function directUpdateCalendarHeader() {
    const monthNames = [
        'January', 'February', 'March', 'April', 'May', 'June', 
        'July', 'August', 'September', 'October', 'November', 'December'
    ];
    
    document.getElementById('direct-current-month-display').textContent = 
        `${monthNames[directCurrentMonth]} ${directCurrentYear}`;
}

/**
 * Get the number of days in a month
 * @param {number} year - The year
 * @param {number} month - The month (0-11)
 * @returns {number} The number of days in the month
 */
function directGetDaysInMonth(year, month) {
    return new Date(year, month + 1, 0).getDate();
}

/**
 * Format a date string in YYYY-MM-DD format
 * @param {number} year - The year
 * @param {number} month - The month (1-12)
 * @param {number} day - The day
 * @returns {string} The formatted date string
 */
function directFormatDateString(year, month, day) {
    // Format month and day with leading zeros
    const monthStr = month.toString().padStart(2, '0');
    const dayStr = day.toString().padStart(2, '0');
    return `${year}-${monthStr}-${dayStr}`;
}

/**
 * Generate the calendar days
 */
function directGenerateCalendarDays() {
    const calendarDays = document.getElementById('direct-calendar-days');
    calendarDays.innerHTML = '';
    
    // Get the first day of the month and days in month
    const firstDayOfMonth = new Date(directCurrentYear, directCurrentMonth, 1);
    const startingDayOfWeek = firstDayOfMonth.getDay();
    const daysInCurrentMonth = directGetDaysInMonth(directCurrentYear, directCurrentMonth);
    
    // Calculate previous and next month
    let prevMonthYear = directCurrentYear;
    let prevMonth = directCurrentMonth - 1;
    if (prevMonth < 0) {
        prevMonth = 11;
        prevMonthYear--;
    }
    
    let nextMonthYear = directCurrentYear;
    let nextMonth = directCurrentMonth + 1;
    if (nextMonth > 11) {
        nextMonth = 0;
        nextMonthYear++;
    }
    
    // Get today's date
    const today = new Date();
    const todayYear = today.getFullYear();
    const todayMonth = today.getMonth();
    const todayDay = today.getDate();
    
    // Add days from previous month to fill the first row
    const daysInPrevMonth = directGetDaysInMonth(prevMonthYear, prevMonth);
    for (let i = startingDayOfWeek - 1; i >= 0; i--) {
        const day = daysInPrevMonth - i;
        const display_month = prevMonth + 1; // For display (1-12)
        const dateStr = directFormatDateString(prevMonthYear, display_month, day);
        
        const isToday = (prevMonthYear === todayYear && prevMonth === todayMonth && day === todayDay);
        const isPrimary = (dateStr === directPrimaryDate);
        const isSelected = directSelectedDates.has(dateStr);
        
        directAddDayToCalendar(calendarDays, day, dateStr, 'outside-month', 
            isToday, isPrimary, isSelected, prevMonthYear, display_month, day);
    }
    
    // Add days of current month
    const display_current_month = directCurrentMonth + 1; // For display (1-12)
    for (let day = 1; day <= daysInCurrentMonth; day++) {
        const dateStr = directFormatDateString(directCurrentYear, display_current_month, day);
        
        const isToday = (directCurrentYear === todayYear && directCurrentMonth === todayMonth && day === todayDay);
        const isPrimary = (dateStr === directPrimaryDate);
        const isSelected = directSelectedDates.has(dateStr);
        
        directAddDayToCalendar(calendarDays, day, dateStr, '', 
            isToday, isPrimary, isSelected, directCurrentYear, display_current_month, day);
    }
    
    // Add days from next month to complete the grid
    const totalCells = 42; // 6 rows x 7 columns
    const cellsToAdd = totalCells - (startingDayOfWeek + daysInCurrentMonth);
    const display_next_month = nextMonth + 1; // For display (1-12)
    
    for (let day = 1; day <= cellsToAdd; day++) {
        const dateStr = directFormatDateString(nextMonthYear, display_next_month, day);
        
        const isToday = (nextMonthYear === todayYear && nextMonth === todayMonth && day === todayDay);
        const isPrimary = (dateStr === directPrimaryDate);
        const isSelected = directSelectedDates.has(dateStr);
        
        directAddDayToCalendar(calendarDays, day, dateStr, 'outside-month', 
            isToday, isPrimary, isSelected, nextMonthYear, display_next_month, day);
    }
}

/**
 * Add a day to the calendar
 * @param {HTMLElement} container - The container to add the day to
 * @param {number} day - The day number
 * @param {string} dateStr - The date string in YYYY-MM-DD format
 * @param {string} extraClass - Extra CSS class for styling
 * @param {boolean} isToday - Whether this day is today
 * @param {boolean} isPrimary - Whether this is the primary date
 * @param {boolean} isSelected - Whether this date is selected
 * @param {number} year - The year
 * @param {number} month - The month (1-12)
 * @param {number} dayNum - The day number
 */
function directAddDayToCalendar(container, day, dateStr, extraClass, isToday, isPrimary, isSelected, year, month, dayNum) {
    const dayItem = document.createElement('div');
    dayItem.textContent = day;
    dayItem.className = `day-item${extraClass ? ' ' + extraClass : ''}${isToday ? ' today' : ''}`;
    
    if (isPrimary) {
        dayItem.classList.add('primary-date');
        dayItem.setAttribute('title', 'Primary schedule date');
    } else if (isSelected) {
        dayItem.classList.add('selected');
    }
    
    // Store the date components as data attributes
    dayItem.setAttribute('data-date', dateStr);
    dayItem.setAttribute('data-year', year);
    dayItem.setAttribute('data-month', month);
    dayItem.setAttribute('data-day', dayNum);
    
    // Add click event to select/deselect the date
    if (!isPrimary) {
        dayItem.addEventListener('click', function() {
            // Use the data attributes to get the date string
            const clickedDateStr = this.getAttribute('data-date');
            directToggleDateSelection(clickedDateStr, this);
        });
    } else {
        dayItem.classList.add('disabled');
    }
    
    // Fix the width to make a 7-column grid
    dayItem.style.width = 'calc(100% / 7)';
    
    container.appendChild(dayItem);
}

/**
 * Toggle date selection
 * @param {string} dateStr - The date string in YYYY-MM-DD format
 * @param {HTMLElement} dayItem - The day item element
 */
function directToggleDateSelection(dateStr, dayItem) {
    if (directSelectedDates.has(dateStr)) {
        directSelectedDates.delete(dateStr);
        dayItem.classList.remove('selected');
    } else {
        directSelectedDates.add(dateStr);
        dayItem.classList.add('selected');
    }
    
    // Update form and display
    directUpdateFormWithSelectedDates();
    directUpdateSelectedDatesDisplay();
}

/**
 * Update the form with selected dates
 */
function directUpdateFormWithSelectedDates() {
    let repeatDaysField = document.querySelector('input[name="direct_repeat_days_list"]');
    if (!repeatDaysField) {
        repeatDaysField = document.createElement('input');
        repeatDaysField.type = 'hidden';
        repeatDaysField.name = 'direct_repeat_days_list';
        document.getElementById('schedule_form').appendChild(repeatDaysField);
    }
    
    // Set the value to a comma-separated list of selected dates
    repeatDaysField.value = Array.from(directSelectedDates).join(',');
}

/**
 * Update the display of selected dates
 */
function directUpdateSelectedDatesDisplay() {
    const container = document.getElementById('direct-selected-dates-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (directSelectedDates.size === 0) {
        container.innerHTML = '<span class="text-muted">None selected</span>';
        return;
    }
    
    // Sort dates chronologically
    const sortedDates = Array.from(directSelectedDates).sort();
    
    // Add date tags
    sortedDates.forEach(dateStr => {
        // Parse the date parts
        const parts = dateStr.split('-');
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]);
        const day = parseInt(parts[2]);
        
        // Create a formatted display string (e.g., "Apr 2")
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const displayText = `${monthNames[month-1]} ${day}`;
        
        const dateTag = document.createElement('div');
        dateTag.className = 'date-tag m-1 p-1';
        dateTag.innerHTML = `
            ${displayText}
            <button type="button" class="btn-close btn-close-sm ms-1" aria-label="Remove" 
                    onclick="directRemoveDate('${dateStr}')"></button>
        `;
        container.appendChild(dateTag);
    });
}

/**
 * Remove a date from selection
 * @param {string} dateStr - The date string in YYYY-MM-DD format
 */
function directRemoveDate(dateStr) {
    if (directSelectedDates.has(dateStr)) {
        directSelectedDates.delete(dateStr);
        
        // Update the calendar visual state
        const parts = dateStr.split('-');
        const year = parseInt(parts[0]);
        const month = parseInt(parts[1]);
        const day = parseInt(parts[2]);
        
        const dayItem = document.querySelector(`.day-item[data-year="${year}"][data-month="${month}"][data-day="${day}"]`);
        if (dayItem) {
            dayItem.classList.remove('selected');
        }
        
        // Update form and display
        directUpdateFormWithSelectedDates();
        directUpdateSelectedDatesDisplay();
    }
}

/**
 * Clear all selected dates
 */
function directClearDateSelection() {
    // Clear the set
    directSelectedDates.clear();
    
    // Remove 'selected' class from all day items
    document.querySelectorAll('.day-item.selected').forEach(dayItem => {
        dayItem.classList.remove('selected');
    });
    
    // Update form and display
    directUpdateFormWithSelectedDates();
    directUpdateSelectedDatesDisplay();
}

// Add a global function to get the selected dates
function getDirectSelectedDates() {
    return Array.from(directSelectedDates);
}