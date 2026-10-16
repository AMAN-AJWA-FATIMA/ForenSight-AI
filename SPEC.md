# Project Specification

## 1. Project Title
ForenSight-AI : AI-Powered Criminal Investigation Workspace

## 2. Problem Statement
Criminal investigations often involve large amounts of information distributed across witness statements, incident reports, and evidence records. Manually organizing these documents, reconstructing timelines, and comparing statements can be time-consuming and may make inconsistencies or missing information difficult to identify.

ForenSight-AI is an AI-powered investigation workspace designed to help investigators organize fictional case information, extract relevant facts, reconstruct event timelines, compare witness statements, and flag potential inconsistencies for human review.

The system aims to make investigation documentation more structured and easier to review. It does not determine guilt, identify suspects as perpetrators, or replace professional investigators.

## 3. Objectives
- Develop an AI-powered workspace for organizing investigation cases and documents.
- Extract relevant facts, dates, events, locations, and people from uploaded case documents.
- Generate structured timelines from information found in documents.
- Compare witness statements and flag potential inconsistencies with supporting source references.
- Identify potentially missing information or documentation for further review.
- Store cases, documents, and AI-generated analysis in a persistent database.
- Implement secure user authentication with two-factor authentication (2FA).
- Ensure that each user can access only their own cases and associated information.
- Deliver a working, deployed prototype that demonstrates the complete investigation workflow.

## 4. Target Users
- Criminal investigation professionals who need structured investigation documentation.
- Forensic and investigative teams seeking assistance with reviewing case information.
- Researchers and students interested in AI-assisted document analysis and investigative workflows.

The hackathon prototype will use fictional or synthetic investigation cases for demonstration and testing.

## 5. Functional Requirements
- Allow users to create an account and sign in securely.
- Support two-factor authentication (2FA) for account security.
- Allow authenticated users to create, view, update, and manage their own investigation cases.
- Allow users to upload supported case documents, including PDF and text files.
- Extract readable text from uploaded documents.
- Use live calls to a hosted AI model to analyze case-specific document content.
- Extract key facts, dates, events, people, and locations from documents.
- Generate a chronological timeline of reported events.
- Compare two or more witness statements and flag potential inconsistencies.
- Identify potentially missing information or documentation based on the available case records.
- Display AI-generated findings with references to relevant source documents and passages where available.
- Clearly distinguish information stated in source documents from AI-generated interpretations.
- Allow users to review and save AI analysis results.
- Store case records, document metadata, and analysis results in a persistent database.
- Allow users to retrieve their previously saved cases and analyses after signing out and signing back in.
- Prevent users from accessing another user's private cases and documents.
- Provide clear error messages for unsupported files, failed AI requests, and unsuccessful uploads.

## 6. Non-Functional Requirements

### Performance
- Process supported documents and return AI analysis within a reasonable time.
- Limit document size and input length to maintain reliable processing.
- Display loading indicators while documents are being processed.

### Security
- Require authentication before users can access case information.
- Support two-factor authentication (2FA).
- Enforce user-level data isolation using database access controls and appropriate authorization checks.
- Store API keys and secrets in environment variables, never in public source code.
- Restrict access to uploaded documents and avoid exposing sensitive information through public URLs.
- Use fictional or synthetic case information in the hackathon demonstration.

### Reliability
- Save successfully created cases and completed analyses in persistent storage.
- Preserve saved data across application restarts and subsequent sign-ins.
- Handle AI API failures, invalid files, and database errors gracefully.
- Avoid presenting unsupported AI-generated claims as established facts.

### Usability
- Provide a clean, responsive, and intuitive interface.
- Organize investigation cases and findings into clearly labeled sections.
- Display timelines and potential inconsistencies in an understandable format.
- Provide source references that allow users to verify findings against original documents.
- Clearly communicate that AI findings require human review.

## 7. Technology Stack
- Frontend: Next.js
- UI Styling: Tailwind CSS
- Backend: Next.js server-side API routes or server functions
- Authentication: Supabase Auth with supported multi-factor authentication
- Database: Supabase PostgreSQL
- AI Integration: OpenAI API or another supported hosted AI model
- Document Processing: Python or suitable document-processing libraries
- File Storage: Private Supabase Storage, if required
- Version Control: Git and GitHub
- Deployment: Vercel
- Code Component Publishing: Devmarketplace

The final implementation may use compatible libraries and services based on hackathon resources and build constraints.

## 8. AI/ML Approach

### Data Sources
The prototype will use fictional or synthetic investigation documents, including witness statements, incident reports, and evidence records. No real criminal case data is required for the demonstration.

### AI Model
The system will integrate a hosted large language model through live API calls. The model will analyze document content in the context of the selected investigation case.

### Processing Workflow
1. The user creates an investigation case and uploads supported documents.
2. The system extracts readable text from each document.
3. The application supplies relevant document content and case context to the AI model.
4. The AI model extracts structured facts, events, dates, people, and locations.
5. The system organizes extracted events into a chronological timeline where sufficient date and time information exists.
6. The AI model compares witness statements and identifies potential contradictions or differences.
7. The system identifies potentially missing information based on the supplied documents.
8. Findings are linked to source documents and passages where available.
9. The user reviews the findings and saves the analysis to the database.

### AI Output Validation
- Use structured output formats, such as JSON, for predictable results.
- Validate AI responses against the expected output schema.
- Retain source references to support human verification.
- Mark uncertain or conflicting information for review.
- Avoid treating an absence of information as proof that an event did not occur.
- Do not use AI-generated findings to determine guilt or automatically accuse individuals.

### Evaluation Metrics
The prototype will be evaluated using a manually prepared set of fictional test cases with known facts, timelines, and statement differences.

Evaluation will consider:
- Fact extraction accuracy against the prepared reference information.
- Correct identification of deliberately introduced statement inconsistencies.
- Timeline ordering accuracy where reliable timestamps are available.
- Source-reference correctness.
- Output completeness and adherence to the expected response format.
- Successful handling of ambiguous or incomplete information.

The evaluation will be a prototype-level assessment, not a validated forensic accuracy study.

## 9. Acceptance Criteria
The project will be considered successful when:

- A new user can register and sign in.
- Two-factor authentication can be configured and used successfully.
- Two separate user accounts can access their own data without accessing each other's private cases.
- An authenticated user can create an investigation case.
- The user can upload a supported fictional case document.
- The application extracts text and makes a live API call to the configured AI model.
- The AI generates structured facts and a timeline from the supplied information.
- The application compares witness statements and flags potential inconsistencies for human review.
- AI findings display relevant source references where available.
- The user can save the analysis and retrieve it after signing out and signing back in.
- Saved cases and analyses remain available after an application restart.
- The deployed application works through a complete end-to-end user journey.
- The public GitHub repository contains the required documentation and implementation.
- At least two eligible code components developed during the hackathon are published on Devmarketplace.
- The application handles common processing errors without crashing.

## 10. Scope and Limitations

### In Scope
- User registration, sign-in, and two-factor authentication.
- Private investigation case management.
- Uploading and processing supported fictional case documents.
- AI-powered fact extraction and timeline generation.
- Witness-statement comparison.
- Identification of potential inconsistencies and missing documentation.
- Source-linked AI findings and human review.
- Persistent database storage and retrieval of case analyses.
- Deployment of a functional web application.
- Publishing two reusable code components on Devmarketplace.

### Out of Scope
- Automatically determining who committed a crime.
- Declaring an individual guilty or innocent.
- Predicting criminality or identifying criminals from facial appearance.
- Replacing professional investigators, forensic experts, lawyers, or judicial processes.
- Real-time police surveillance or access to private law-enforcement databases.
- Authenticating physical evidence or proving that evidence is genuine.
- Performing laboratory forensic testing.
- Providing guaranteed conclusions from incomplete or contradictory documents.
- Training a custom forensic AI model from scratch during the hackathon.

### Limitations
- AI outputs may contain errors, omissions, or incorrect interpretations.
- Timeline accuracy depends on the quality and completeness of source documents.
- Statement differences do not necessarily indicate deception; they may result from memory, ambiguity, or recording errors.
- Source references and extracted information must be verified against the original documents.
- The prototype will be tested with fictional or synthetic cases and will not be presented as a validated forensic investigation system.
