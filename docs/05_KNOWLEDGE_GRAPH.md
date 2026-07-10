# IRIS AI — Knowledge Graph Logic & Entity Extraction

This document explains the Knowledge Graph module, showing how documents are parsed into nodes and links, and how they are visualized on the frontend canvas.

---

## 1. Entity Extraction Architecture

When a document is completed, its text is scanned to extract named entities. This is done in the `DocumentProcessor._extract_local_entities` and `KnowledgeGraphService.link_document_entities` services.

### Named Entity Types Extracted
- **PERSON**: Individual names (e.g., "Praveen Kumar").
- **ORG**: Organizations and boards (e.g., "CBSE Board", "BESCOM", "Apollo Clinic").
- **DATE**: Years or dates of relevance (e.g., "2011", "15/08/1995").
- **ID_NUMBER**: Registration details (e.g., PAN, DL, Aadhaar card numbers, Consumer IDs).
- **GPE**: Places and locations (e.g., "Bangalore", "Karnataka").

---

## 2. Graph Relationship Mappings

We map overlapping entities to establish **8 relationship categories** between nodes:

1. `ISSUED_TO`: Links a document node to a Person entity (e.g. `PAN Card` -> `ISSUED_TO` -> `Praveen Kumar`).
2. `ISSUED_BY`: Links a document to the publishing body ORG (e.g. `PAN Card` -> `ISSUED_BY` -> `Income Tax Department`).
3. `STUDIED_AT`: Links academic records to the school ORG (e.g. `Class 10 Marksheet` -> `STUDIED_AT` -> `Kendriya Vidyalaya`).
4. `EMPLOYED_AT`: Links employment documents to the employer ORG (e.g. `Offer Letter` -> `EMPLOYED_AT` -> `Tech Solutions Inc`).
5. `RELATED_TO`: Links documents together if they share identical entities (e.g. `Aadhaar Card` and `PAN Card` reference the same Person).
6. `PRECEDES` & `FOLLOWS`: Links academic documents chronologically by year (e.g. `Class 10 Marksheet` -> `PRECEDES` -> `Class 12 Marksheet`).
7. `CONTRADICTS`: Highlights anomalies, such as when two documents list different Dates of Birth for the same Person (e.g. `Aadhaar DOB` != `PAN DOB`).

---

## 3. Database Entity Representation

Graph data is stored in the SQLite `graph_edges` table:

| Field | Type | Description |
|---|---|---|
| `source_id` | String | Source node identifier (Document UUID or Entity string). |
| `target_id` | String | Target node identifier. |
| `source_name` | String | Plain-text display label of source. |
| `target_name` | String | Plain-text display label of target. |
| `source_type` | String | "document" or "entity". |
| `target_type` | String | "document" or "entity". |
| `relationship_type` | String | The relationship tag (e.g. `ISSUED_TO`). |

---

## 4. Frontend Rendering Layout (React Flow)

To render this data without overlapping nodes, `KnowledgeGraph.tsx` implements a **radial circle-packing algorithm**:

- **Inner Ring:** Document nodes are arranged in a circular formation at a radius of 220px.
- **Outer Ring:** Entity nodes (e.g. names, dates) are placed at an outer radius of 420px.

$$X = Center_X + Radius \times \cos(\theta)$$
$$Y = Center_Y + Radius \times \sin(\theta)$$

This structure ensures document nodes remain centered and easily readable, while entity links branch outwards clearly.
