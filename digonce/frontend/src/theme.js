/**
 * NagarSync Enterprise Design Tokens
 * Official Palette: "Visionary Governance for a Brighter Society" (8 colors)
 *
 * Primary Deep Navy:     #003366
 * Ocean Corporate Blue:  #0099CC
 * Bright Vivid Blue:     #0099CC
 * Soft Sky / Ice Blue:   #A2C2E2
 * Clean Silver Grey:     #B0B0B0
 * Pure Crisp White:      #FFFFFF
 * Vivid Gold / Amber:    #FFCC00
 * Warm Tangerine Orange: #FF9933
 */

export const palette = {
  deepNavy: '#003366',
  oceanBlue: '#0099CC',
  vividBlue: '#0099CC',
  skyBlue: '#A2C2E2',
  silverGrey: '#B0B0B0',
  white: '#FFFFFF',
  goldYellow: '#FFCC00',
  tangerineOrange: '#FF9933',
}

export const theme = {
  colors: {
    // Canvas & Surfaces
    canvas: '#FFFFFF',         // Ultra-light navy-slate wash
    canvasSubtle: '#FFFFFF',
    surface: '#FFFFFF',        // Pure white (#FFFFFF)
    surfaceSubtle: '#FFFFFF',  // Soft ice-blue wash
    surfaceTint: '#FFFFFF',

    // Borders
    border: '#FFFFFF',
    borderMedium: '#A2C2E2',   // Soft Ice Blue (#A2C2E2)
    borderAccent: '#A2C2E2',   // Soft Ice Blue (#A2C2E2)
    borderFocus: '#0099CC',

    // Brand Colors
    primaryNavy: '#003366',    // Deep Navy (#003366)
    primaryNavyHover: '#0099CC',
    oceanBlue: '#0099CC',      // Ocean Blue (#0099CC)
    oceanBlueHover: '#0099CC',
    vividBlue: '#0099CC',      // Bright Vivid Blue (#0099CC)
    vividBlueHover: '#0099CC',
    skyBlue: '#A2C2E2',        // Ice Blue (#A2C2E2)
    silverGrey: '#B0B0B0',     // Neutral Silver (#B0B0B0)

    // Typography
    inkPrimary: '#003366',     // Deep Navy for headlines and prominent text
    inkBody: '#003366',        // Deep navy for readable body copy
    inkSecondary: '#006699',   // Secondary navy-blue
    inkMuted: '#006699',       // Muted but accessible slate-blue

    // Semantic States (Mapped from the 8-color palette)
    state: {
      healthy: '#0099CC',      // Deep Ocean Blue for verified/stable
      info: '#0099CC',         // Vivid Cyan Blue for telemetry & live feeds
      warning: '#FFCC00',      // Golden Yellow for caution/moderate alerts
      critical: '#FF9933',     // Warm Tangerine Orange for urgent hazards
      emergency: '#FF9933',    // Warm tangerine from the project palette
    }
  },
  typography: {
    fontSans: "'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
  }
}

export default theme
