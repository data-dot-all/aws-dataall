import {util} from '@aws-appsync/utils';
import {select, createPgStatement, toJsonObject} from '@aws-appsync/utils/rds';

/**
 * Sends a request to get an item with emp_no `ctx.args.emp_no` from the employees table.
 * @param {import('@aws-appsync/utils').Context} ctx the context
 * @returns {*} the request
 */
export function request(ctx) {
    return createPgStatement(select({table: 'dev.organization'}));
}


/**
 * Returns the result or throws an error if the operation failed.
 * @param {import('@aws-appsync/utils').Context} ctx the context
 * @returns {*} the result
 */
export function response(ctx) {
    const {error, result} = ctx;
    if (error) {
        return util.appendError(error.message, error.type, result);
    }
    return toJsonObject(result)[0];
}
