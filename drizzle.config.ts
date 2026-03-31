import { defineConfig } from "drizzle-kit";

export default defineConfig({
  out: "./drizzle",
  schema: "./shared/schema.ts",
  dialect: "postgresql",
  dbCredentials: {
    url: process.env.DATABASE_URL!,
  },
  tablesFilter: [
    "!spatial_ref_sys",
    "!geometry_columns",
    "!geography_columns",
    "!raster_columns",
    "!raster_overviews",
    "!layer",
    "!topology",
  ],
});
