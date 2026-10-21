/**
 * The generated vocabularies must equal the published contract.
 *
 * `docs/openapi.json` is the single source of truth (BE-1 published the triage and
 * complaint vocabularies there). `npm run gen:api` derives `enums.js` from it; this
 * test proves the committed output has not drifted from the contract, so a client
 * can never offer a value the API rejects.
 */
import { describe, expect, it } from 'vitest';
import openapi from '../../../../docs/openapi.json';
import { complaintCategories, complaintPriorities, triageCategories, triageDecisions, triagePriorities, triageTrades, } from './enums';
function enumAt(schema, field) {
    const schemas = openapi.components.schemas;
    const node = schemas[schema]?.properties?.[field];
    if (!node)
        throw new Error(`No schema field ${schema}.${field} in docs/openapi.json.`);
    const inline = node.enum;
    if (inline)
        return inline;
    const branch = node.anyOf?.find((candidate) => candidate.enum);
    if (!branch?.enum)
        throw new Error(`${schema}.${field} publishes no enum.`);
    return branch.enum;
}
describe('generated enums equal the OpenAPI vocabulary', () => {
    it('matches the complaint fields', () => {
        expect([...complaintCategories]).toEqual(enumAt('ComplaintCreate', 'category'));
        expect([...complaintPriorities]).toEqual(enumAt('ComplaintCreate', 'priority'));
    });
    it('matches the triage decision and suggestion fields', () => {
        expect([...triageCategories]).toEqual(enumAt('TriageDecisionRequest', 'category'));
        expect([...triagePriorities]).toEqual(enumAt('TriageDecisionRequest', 'priority'));
        expect([...triageTrades]).toEqual(enumAt('TriageDecisionRequest', 'trade'));
        expect([...triageDecisions]).toEqual(enumAt('TriageDecisionRequest', 'decision'));
        expect(enumAt('TriageSuggestionResponse', 'suggested_category')).toEqual([...triageCategories]);
        expect(enumAt('TriageSuggestionResponse', 'suggested_priority')).toEqual([...triagePriorities]);
        expect(enumAt('TriageSuggestionResponse', 'suggested_trade')).toEqual([...triageTrades]);
        expect(enumAt('TriageSuggestionResponse', 'decided_category')).toEqual([...triageCategories]);
        expect(enumAt('TriageSuggestionResponse', 'decided_priority')).toEqual([...triagePriorities]);
        expect(enumAt('TriageSuggestionResponse', 'decided_trade')).toEqual([...triageTrades]);
    });
    it('publishes non-empty, unique, snake_case values', () => {
        for (const values of [
            complaintCategories,
            complaintPriorities,
            triageCategories,
            triagePriorities,
            triageTrades,
            triageDecisions,
        ]) {
            expect(values.length).toBeGreaterThan(0);
            expect(new Set(values).size).toBe(values.length);
            for (const value of values)
                expect(value).toMatch(/^[a-z][a-z0-9_]*$/);
        }
    });
});
