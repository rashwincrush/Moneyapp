// Global variables
let categories = [];
let currentTransactions = [];
let sortDirection = 'desc'; // Start with newest first
let pieChart = null;
let barChart = null;

document.addEventListener('DOMContentLoaded', async function() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');
    const form = document.getElementById('uploadForm');
    const clearAllButton = document.getElementById('clearAll');
    const dateSort = document.getElementById('dateSort');
    const transactionsBody = document.getElementById('transactionsBody');
    const submitCategoriesButton = document.getElementById('submitCategories');

    // First load categories, then load transactions
    try {
        await loadCategories();
        await loadTransactions();
    } catch (error) {
        console.error('Error during initialization:', error);
        // Initialize empty state if data loading fails
        categories = [];
        currentTransactions = [];
        updateSummary({
            total_credit: 0,
            total_debit: 0,
            transactions: []
        });
    }
    // Date sorting
    dateSort.addEventListener('click', () => {
        sortDirection = sortDirection === 'asc' ? 'desc' : 'asc';
        sortAndDisplayTransactions();
    });

    // Clear all data
    clearAllButton.addEventListener('click', async () => {
        if (confirm('Are you sure you want to clear all transaction data? This cannot be undone.')) {
            try {
                const response = await fetch('/transactions/clear', {
                    method: 'POST'
                });
                if (response.ok) {
                    // Reload transactions to update UI
                    await loadTransactions();
                    alert('All transaction data has been cleared.');
                }
            } catch (error) {
                console.error('Error clearing data:', error);
                alert('Error clearing data. Please try again.');
            }
        }
    });

    // Drag and drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('drag-over');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('drag-over');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length) {
            handleFiles(e.target.files);
        }
    });

    async function handleFiles(files) {
        // Show loading state
        dropZone.classList.add('loading');
        let totalProcessed = 0;
        let totalSkipped = 0;
        let errors = [];

        try {
            for (const file of files) {
                const formData = new FormData();
                
                // Choose endpoint based on file type
                let endpoint;
                if (file.type.startsWith('image/')) {
                    endpoint = '/transactions/process';
                    formData.append('image', file);
                } else {
                    endpoint = '/transactions/process-statement';
                    formData.append('file', file);
                }

                try {
                    const response = await fetch(endpoint, {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();
                    console.log('Response:', data);

                    if (response.ok) {
                        totalProcessed++;
                    } else {
                        console.error(`Error processing ${file.name}:`, data);
                        errors.push(`${file.name}: ${data.detail || 'Unknown error'}`);
                        totalSkipped++;
                    }
                } catch (error) {
                    console.error(`Error processing ${file.name}:`, error);
                    errors.push(`${file.name}: ${error.message}`);
                    totalSkipped++;
                }
            }

            // Reload transactions after processing
            await loadTransactions();

            // Show summary
            if (totalProcessed > 0) {
                alert(`Successfully processed ${totalProcessed} file(s)${totalSkipped > 0 ? `, ${totalSkipped} file(s) had errors` : ''}`);
            } else if (totalSkipped > 0) {
                alert(`Failed to process ${totalSkipped} file(s). Errors:\n${errors.join('\n')}`);
            }

        } catch (error) {
            console.error('Error processing files:', error);
            alert('Error processing files. Please try again.');
        } finally {
            // Hide loading state
            dropZone.classList.remove('loading');
        }
    }

    async function loadCategories() {
        try {
            const response = await fetch('/categories');
            const data = await response.json();
            categories = data.categories;
            console.log('Categories loaded:', categories);
        } catch (error) {
            console.error('Error loading categories:', error);
            categories = ['Other']; // Fallback category if loading fails
        }
    }

    async function loadTransactions() {
        try {
            const response = await fetch('/transactions/summary');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Loaded transaction data:', data);

            if (response.ok) {
                updateSummary(data);
                currentTransactions = data.transactions || [];
                await sortAndDisplayTransactions();
                
                // Force chart update
                console.log('Updating charts after loading transactions');
                updateCharts(currentTransactions);
                return currentTransactions;
            }
        } catch (error) {
            console.error('Error loading transactions:', error);
            currentTransactions = [];
            updateSummary({
                total_credit: 0,
                total_debit: 0,
                transactions: []
            });
            displayTransactions([]);
            updateCharts([]);
        }
    }

    function updateSummary(data) {
        document.getElementById('totalCredit').textContent = formatCurrency(data.total_credit || 0);
        document.getElementById('totalDebit').textContent = formatCurrency(data.total_debit || 0);
        document.getElementById('netBalance').textContent = formatCurrency((data.total_credit || 0) - (data.total_debit || 0));
    }

    async function sortAndDisplayTransactions() {
        if (!currentTransactions) return;

        currentTransactions.sort((a, b) => {
            const dateA = new Date(a.date || a.timestamp);
            const dateB = new Date(b.date || b.timestamp);
            return sortDirection === 'asc' ? dateA - dateB : dateB - dateA;
        });

        displayTransactions(currentTransactions);
    }

    function displayTransactions(transactions) {
        const tbody = document.getElementById('transactionsBody');
        tbody.innerHTML = '';

        transactions.forEach((transaction, index) => {
            const row = document.createElement('tr');
            row.className = index % 2 === 0 ? 'bg-white' : 'bg-gray-50';

            // Format date
            const date = new Date(transaction.date);
            const formattedDate = date.toLocaleDateString('en-IN', {
                day: '2-digit',
                month: 'short',
                year: 'numeric'
            });

            // Create row content
            row.innerHTML = `
                <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                    ${formattedDate}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${transaction.description}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${transaction.bank || 'N/A'}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm ${transaction.type === 'credit' ? 'text-green-600' : 'text-red-600'}">
                    ${transaction.type === 'credit' ? '+' : '-'}${formatCurrency(transaction.amount)}
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                    ${createCategoryDropdown(transaction, index)}
                </td>
            `;

            tbody.appendChild(row);
        });

        // Initialize category dropdowns
        transactions.forEach((transaction, index) => {
            const select = document.getElementById(`category-${index}`);
            if (select) {
                select.value = transaction.category || 'Uncategorized';
            }
        });
    }

    function createCategoryDropdown(transaction, index) {
        console.log(`Creating dropdown for transaction ${index}`); // Log when creating dropdown
        const select = document.createElement('select');
        select.id = `category-${index}`;
        select.className = 'px-2 py-1 border rounded text-sm transition-colors duration-200 category-dropdown';
        select.dataset.transactionId = index;

        // Sort categories with 'Other' at the end
        const sortedCategories = [...categories].sort((a, b) => {
            if (a === 'Other') return 1;
            if (b === 'Other') return -1;
            return a.localeCompare(b);
        });

        sortedCategories.forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category;
            option.selected = (transaction.category || 'Other') === category;
            select.appendChild(option);
        });

        // Modified event listener with improved error handling and chart updates
        select.addEventListener('change', async (e) => {
            console.log('Category dropdown changed'); // Log when dropdown value changes
            const transactionId = parseInt(e.target.dataset.transactionId);
            const newCategory = e.target.value;
            const oldCategory = transaction.category || 'Other';

            select.style.backgroundColor = '#e8f0fe';  // Visual feedback

            try {
                const response = await fetch(`/transactions/${transactionId}/category`, {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ category: newCategory })
                });

                if (!response.ok) {
                    throw new Error(await response.text());
                }

                // Update local data
                transaction.category = newCategory;

                // Force a full data refresh
                await loadTransactions();

                // Explicitly trigger chart updates
                updateCharts(currentTransactions);

                // Success feedback
                select.style.backgroundColor = '#ecfdf5';
                setTimeout(() => {
                    select.style.backgroundColor = '';
                }, 1000);

            } catch (error) {
                console.error('Error updating category:', error);
                // Revert the category
                transaction.category = oldCategory;
                select.value = oldCategory;

                select.style.backgroundColor = '#fef2f2';
                setTimeout(() => {
                    select.style.backgroundColor = '';
                }, 1000);

                alert('Failed to update category. Please try again.');
            }
        });

        return select.outerHTML;
    }

    function updateCharts(transactions) {
        if (!transactions || transactions.length === 0) {
            console.log('No transactions to display in charts');
            return;
        }

        const categoryData = {};
        const categoryColors = {
            'Food & Dining': '#FF6384',
            'Shopping': '#36A2EB',
            'Transportation': '#FFCE56',
            'Bills & Utilities': '#4BC0C0',
            'Entertainment': '#9966FF',
            'Health & Medical': '#FF9F40',
            'Travel': '#FF99CC',
            'Education': '#7CBA3B',
            'Business': '#B2B2B2',
            'Investments': '#668B8B',
            'Salary': '#32CD32',
            'Other': '#C0C0C0'
        };

        // Initialize all categories with zero values
        categories.forEach(category => {
            categoryData[category] = {
                credit: 0,
                debit: 0,
                total: 0  // Add total for easier calculations
            };
        });

        // Process transactions with improved error handling
        transactions.forEach(transaction => {
            const category = transaction.category || 'Other';
            const amount = parseFloat(transaction.amount) || 0;
            
            if (transaction.type === 'credit') {
                categoryData[category].credit += amount;
            } else {
                categoryData[category].debit += amount;
            }
            categoryData[category].total += amount;
        });

        // Prepare chart data
        const pieData = {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [],
                hoverOffset: 4
            }]
        };

        const barData = {
            labels: [],
            datasets: [
                {
                    label: 'Credit',
                    data: [],
                    backgroundColor: 'rgba(75, 192, 192, 0.5)',
                    borderColor: 'rgb(75, 192, 192)',
                    borderWidth: 1
                },
                {
                    label: 'Debit',
                    data: [],
                    backgroundColor: 'rgba(255, 99, 132, 0.5)',
                    borderColor: 'rgb(255, 99, 132)',
                    borderWidth: 1
                }
            ]
        };

        // Sort categories by total amount
        const sortedCategories = Object.entries(categoryData)
            .sort((a, b) => Math.abs(b[1].total) - Math.abs(a[1].total))
            .map(([category]) => category);

        // Populate chart data
        sortedCategories.forEach(category => {
            const data = categoryData[category];
            if (data.credit !== 0 || data.debit !== 0) {
                pieData.labels.push(category);
                pieData.datasets[0].data.push(Math.abs(data.total));
                pieData.datasets[0].backgroundColor.push(categoryColors[category] || '#808080');

                barData.labels.push(category);
                barData.datasets[0].data.push(data.credit);
                barData.datasets[1].data.push(Math.abs(data.debit));
            }
        });

        // Update pie chart with destroy and recreate
        if (pieChart) {
            pieChart.destroy();
        }
        const pieCtx = document.getElementById('categoryPieChart').getContext('2d');
        pieChart = new Chart(pieCtx, {
            type: 'pie',
            data: pieData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            font: { size: 12 }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Total Spending by Category',
                        font: { size: 16 }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `₹${value.toLocaleString('en-IN')} (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });

        // Update bar chart with destroy and recreate
        if (barChart) {
            barChart.destroy();
        }
        const barCtx = document.getElementById('categoryBarChart').getContext('2d');
        barChart = new Chart(barCtx, {
            type: 'bar',
            data: barData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return '₹' + value.toLocaleString('en-IN');
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'top'
                    },
                    title: {
                        display: true,
                        text: 'Credit vs Debit by Category',
                        font: { size: 16 }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.raw;
                                return `₹${Math.abs(value).toLocaleString('en-IN')}`;
                            }
                        }
                    }
                }
            }
        });

        // Log chart updates for debugging
        console.log('Charts updated with transactions:', transactions.length);
    }

    // Add function to force reload data and charts
    async function forceRefresh() {
        try {
            await loadTransactions();
            console.log('Data refreshed successfully');
        } catch (error) {
            console.error('Error refreshing data:', error);
        }
    }

    // Bank statement handling
    const screenshotTab = document.getElementById('screenshotTab');
    const statementTab = document.getElementById('statementTab');
    const screenshotUpload = document.getElementById('screenshotUpload');
    const statementUpload = document.getElementById('statementUpload');
    const statementInput = document.getElementById('statementInput');
    const statementForm = document.getElementById('statementForm');

    // Tab switching
    screenshotTab.addEventListener('click', () => {
        screenshotTab.classList.add('text-indigo-600', 'border-indigo-600');
        statementTab.classList.remove('text-indigo-600', 'border-indigo-600');
        screenshotUpload.classList.remove('hidden');
        statementUpload.classList.add('hidden');
    });

    statementTab.addEventListener('click', () => {
        statementTab.classList.add('text-indigo-600', 'border-indigo-600');
        screenshotTab.classList.remove('text-indigo-600', 'border-indigo-600');
        statementUpload.classList.remove('hidden');
        screenshotUpload.classList.add('hidden');
    });

    // Process bank statement files
    async function processStatementFiles(files) {
        const maxSize = 10 * 1024 * 1024; // 10MB
        const validTypes = {
            'application/pdf': true,
            'text/csv': true,
            'image/png': true,
            'image/jpeg': true
        };

        let successCount = 0;
        let errorCount = 0;

        for (const file of files) {
            if (file.size > maxSize) {
                alert(`File ${file.name} is too large. Maximum size is 10MB.`);
                errorCount++;
                continue;
            }

            if (!validTypes[file.type]) {
                alert(`File ${file.name} is not a supported format. Please upload PDF, CSV, PNG, or JPG files.`);
                errorCount++;
                continue;
            }

            const formData = new FormData();

            try {
                // Always use process-statement endpoint for all file types
                const endpoint = '/transactions/process-statement';
                formData.append('file', file);

                const response = await fetch(endpoint, {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();
                console.log('Response:', data);

                if (response.ok) {
                    successCount++;
                } else {
                    console.error(`Error processing ${file.name}:`, data);
                    alert(`Error processing ${file.name}: ${data.detail || 'Unknown error'}`);
                    errorCount++;
                }
            } catch (error) {
                console.error(`Error processing ${file.name}:`, error);
                alert(`Error processing ${file.name}: ${error.message}`);
                errorCount++;
            }
        }

        // Reload transactions after all files are processed
        await loadTransactions();

        // Show summary
        if (successCount > 0) {
            alert(`Successfully processed ${successCount} file(s)${errorCount > 0 ? `, ${errorCount} file(s) had errors` : ''}`);
        } else if (errorCount > 0) {
            alert(`Failed to process ${errorCount} file(s)`);
        }
    }

    // Bank statement upload handling
    statementInput.addEventListener('change', async (e) => {
        const files = Array.from(e.target.files);
        if (files.length === 0) return;
        await processStatementFiles(files);
        statementInput.value = ''; // Clear the file input
    });

    // Add drag and drop for bank statements
    const statementDropZone = statementInput.closest('div');
    
    statementDropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        statementDropZone.classList.add('border-indigo-500');
    });

    statementDropZone.addEventListener('dragleave', () => {
        statementDropZone.classList.remove('border-indigo-500');
    });

    statementDropZone.addEventListener('drop', async (e) => {
        e.preventDefault();
        statementDropZone.classList.remove('border-indigo-500');

        const files = Array.from(e.dataTransfer.files);
        if (files.length === 0) return;
        
        await processStatementFiles(files);
    });

    submitCategoriesButton.addEventListener('click', async () => {
        const updatedCategories = {};
        
        // Assuming you have a way to identify each transaction's dropdown
        document.querySelectorAll('.category-dropdown').forEach(select => {
            const transactionId = parseInt(select.dataset.transactionId);
            const selectedCategory = select.value;
            updatedCategories[transactionId] = selectedCategory;
        });

        try {
            const response = await fetch('/transactions/update-categories', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedCategories)
            });

            if (!response.ok) {
                throw new Error(await response.text());
            }

            console.log('Categories updated successfully');
            await loadTransactions(); // Refresh the transactions and charts

        } catch (error) {
            console.error('Error updating categories:', error);
            alert('Failed to update categories. Please try again.');
        }
    });
});

function formatCurrency(amount) {
    return new Intl.NumberFormat('en-IN', {
        style: 'currency',
        currency: 'INR'
    }).format(amount);
}
