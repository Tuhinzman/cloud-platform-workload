// Copyright The OpenTelemetry Authors
// SPDX-License-Identifier: Apache-2.0

// Modified from the upstream OpenTelemetry Demo release 2.2.0.
// Change: the unused ProductReview import specifier was removed.

import type { NextApiRequest, NextApiResponse } from 'next';
import InstrumentationMiddleware from '../../../../utils/telemetry/InstrumentationMiddleware';
import { Empty } from '../../../../protos/demo';
import ProductReviewService from '../../../../services/ProductReview.service';

type TResponse = string | Empty;

const handler = async ({ method, query }: NextApiRequest, res: NextApiResponse<TResponse>) => {

    switch (method) {
        case 'GET': {
            const { productId = '' } = query;

            const averageScore = await ProductReviewService.getAverageProductReviewScore(productId as string);

            return res.status(200).json(averageScore);
        }

        default: {
            return res.status(405).send('');
        }
    }
};

export default InstrumentationMiddleware(handler);
