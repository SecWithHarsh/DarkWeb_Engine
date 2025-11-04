# Testing Guide - Explicit Warning Feature

## Quick Test Steps

### Test 1: Normal Search (No Warning)
1. Go to home page: `http://your-server-ip:8000/`
2. Enter keyword: `marketplace`
3. Select at least one search source
4. Click "SEARCH"
5. **Expected**: Search proceeds immediately, no warning popup

### Test 2: Explicit Keyword (With Warning)
1. Go to home page
2. Enter keyword: `drugs`
3. Select at least one search source
4. Click "SEARCH"
5. **Expected**: 
   - ⚠️ Red warning modal appears
   - Shows: "Search term: 'drugs' is flagged as potentially sensitive"
   - Two buttons shown: "❌ CANCEL" and "✅ I UNDERSTAND - SHOW RESULTS"

### Test 3: Cancel Warning
1. Follow Test 2 steps 1-5
2. Click "❌ CANCEL"
3. **Expected**:
   - Modal closes
   - You're back at search form
   - Keyword is still in the input field
   - Can edit and search again

### Test 4: Proceed with Warning
1. Follow Test 2 steps 1-5
2. Click "✅ I UNDERSTAND - SHOW RESULTS"
3. **Expected**:
   - Modal closes
   - Search proceeds normally
   - Results page loads with progress bar
   - Links are checked and displayed

### Test 5: Multiple Explicit Keywords
Test with these keywords to verify warning triggers:
- ✅ `weapon` - Should show warning
- ✅ `porn` - Should show warning
- ✅ `hacking` - Should show warning
- ✅ `credit card` - Should show warning
- ✅ `cannabis` - Should show warning
- ❌ `books` - Should NOT show warning
- ❌ `forum` - Should NOT show warning

### Test 6: Keyword Substring Match
1. Enter: `drugstore` (contains "drug")
2. **Expected**: Warning triggers (substring match)
3. Enter: `drugs test` (contains "drug")
4. **Expected**: Warning triggers

### Test 7: Case Insensitive
1. Enter: `DRUGS` (uppercase)
2. **Expected**: Warning still triggers
3. Enter: `DrUgS` (mixed case)
4. **Expected**: Warning still triggers

## Visual Verification

### Warning Modal Should Show:
- ⚠️ Large warning icon (shaking animation)
- Red/orange color scheme
- Clear heading: "EXPLICIT CONTENT WARNING"
- The exact keyword that triggered it (in red)
- 4 bullet points of acknowledgment
- Yellow highlight: "⚠️ Results will be displayed if you proceed."
- Two clear action buttons

### Modal Behavior:
- ✅ Can close by clicking "❌ CANCEL"
- ✅ Can close by clicking outside modal (on dark background)
- ✅ Can close by pressing ESC key
- ✅ Modal has pulsing glow effect (red shadow)
- ✅ Warning icon shakes

## Edge Cases to Test

### Empty Search
1. Leave keyword blank
2. Click "SEARCH"
3. **Expected**: Error message "Please enter a search keyword"

### No Sources Selected
1. Enter any keyword
2. Don't check any sources
3. Click "SEARCH"
4. **Expected**: Error message "Please select at least one search source"

### Multiple Warnings (Same Session)
1. Search for "drugs" → See warning → Cancel
2. Search for "weapons" → See warning → Cancel
3. Search for "drugs" again → See warning → Proceed
4. **Expected**: Each time warning shows correctly

## Integration Test

### Full Flow Test
1. Start at home page
2. Enter: `marketplace drugs`
3. Select "Ahmia" and "Torch" sources
4. Click "SEARCH"
5. **Expected**: Warning modal appears
6. Click "✅ I UNDERSTAND - SHOW RESULTS"
7. **Expected**: 
   - Redirected to results page
   - Progress bar shows checking links
   - Live results appear as links are verified
   - Can click on links to investigate or sandbox

## Browser Console Check

Open browser DevTools (F12) and check:
- ❌ No JavaScript errors
- ❌ No 404 errors for resources
- ✅ Form submission logs show up
- ✅ No CSRF errors

## Performance Test

1. Search for explicit keyword
2. Click proceed quickly (within 1 second of modal appearing)
3. **Expected**: Form submits correctly without errors

## Accessibility Test

1. Use keyboard only:
   - TAB to navigate to keyword input
   - Type explicit keyword
   - TAB to search button
   - Press ENTER
   - **Expected**: Warning modal appears
   - Press TAB to reach buttons
   - Press ENTER on "CANCEL"
   - **Expected**: Modal closes

2. Press ESC when modal is open
   - **Expected**: Modal closes

## Known Working Keywords

### Will Trigger Warning ⚠️:
- drug, drugs
- weapon, weapons
- porn, adult, sex
- hack, hacking
- cocaine, heroin, meth
- gun, guns
- kill, murder, hitman
- cannabis, weed
- explosives, bomb
- counterfeit, fake id
- child, cp
- gore, snuff

### Will NOT Trigger Warning ✅:
- marketplace
- forum
- search
- bitcoin
- wiki
- books
- blog
- news
- chat
- email

## Success Criteria

✅ Warning appears for explicit keywords
✅ Warning does NOT appear for normal keywords
✅ User can cancel and go back
✅ User can proceed and see results
✅ No errors in console
✅ Modal styling is correct
✅ Buttons are clickable and work
✅ ESC key closes modal
✅ Clicking outside closes modal
✅ Case insensitive matching works
✅ Substring matching works

## Troubleshooting

### If Warning Doesn't Appear:
1. Check browser console for JavaScript errors
2. Verify `explicitKeywords` array is defined in the script
3. Check if `checkExplicitKeyword()` function exists
4. Verify form has `onsubmit="return checkExplicitKeyword(event)"`

### If Proceed Button Doesn't Work:
1. Check if `pendingFormSubmit` flag is being set
2. Verify `proceedWithRisk()` function calls `form.submit()`
3. Check if form ID is correct: `searchForm`

### If Modal Won't Close:
1. Check if `closeExplicitWarning()` function exists
2. Verify modal ID is correct: `explicitModal`
3. Check ESC key listener is registered

## Report Issues

If you find any issues during testing:
1. Note the exact keyword used
2. Note browser and version
3. Check browser console for errors
4. Take screenshot of issue
5. Note expected vs actual behavior

